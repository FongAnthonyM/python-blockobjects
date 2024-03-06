""" multiprocessingexecutor.py.py

"""
# Package Header #
from ...header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Standard Libraries #
from asyncio import run, Future, Task, create_task, iscoroutine, sleep
from asyncio.events import AbstractEventLoop, _get_running_loop
from typing import Any
from warnings import warn

# Third-Party Packages #
from baseobjects import BaseObject

# Local Packages #
from ..context import ProxyInterface
from .futures import PipeFuture
from .synchronize import MultiProcessingEvent
from .queues import MultiProcessingQueue
from .process import Process


# Definitions #
# Classes #
class MultiProcessingProxy(ProxyInterface):
    """An object to act as an execution interface to an object in an asynchronous loop or on a different process.

    Class Attributes:

    Attributes:

    Args:

    """
    # Attributes #
    name: str = ""
    _is_async: bool = True
    _is_process: bool = False
    event_loop: AbstractEventLoop | None = None

    sets_up: bool = True
    tears_down: bool = True
    loop_event: MultiProcessingEvent
    _alive_event: MultiProcessingEvent
    futures: list[Future]

    send_queue: MultiProcessingQueue

    object: Any = None

    process: Process | None = None
    _daemon: bool | None = None

    # Properties #
    @property
    def is_process(self) -> bool:
        """bool: If this object will run in a separate process. It will detect if it is in a process while running.

        When set it will raise an error if the TaskBlock is running.
        """
        if self.is_alive():
            return self.process is not None and self.process.is_alive()
        else:
            return self._is_process

    @is_process.setter
    def is_process(self, value: bool) -> None:
        if self.is_alive():
            raise ValueError("Cannot set process while task is alive.")
        else:
            self._is_process = value

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        obj: Any = None,
        *,
        loop: AbstractEventLoop | None = None,
        init: bool = True,
    ) -> None:
        # Attributes #
        self.event_loop = _get_running_loop()

        self.loop_event = MultiProcessingEvent()
        self._alive_event = MultiProcessingEvent()
        self.futures = []

        self.send_queue = MultiProcessingQueue()

        self.process = Process()

        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct(obj=obj, loop=loop)

    # Pickling
    def __getstate__(self) -> dict[str, Any]:
        """Creates a dictionary of attributes which can be used to rebuild this object.

        Returns:
            dict: A dictionary of this object's attributes.
        """
        out_dict = super().__getstate__()
        del out_dict["process"]
        return out_dict

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Builds this object based on a dictionary of corresponding attributes.

        Args:
            state: The attributes to build this object from.
        """
        state["process"] = Process()
        super().__setstate__(state)

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        obj: Any = None,
        *,
        loop: AbstractEventLoop | None = None,
        init: bool = True,
    ) -> None:
        if obj is not None:
            self.object = obj

        if loop is not None:
            self.event_loop = loop

        super().construct()

    # State
    def is_alive(self) -> bool:
        """Checks if this object is currently running.

        Returns:
            bool: If this object is currently running.
        """
        return self._alive_event.is_set()

    def is_processing(self) -> bool:
        """Checks if this object is currently running in a process.

        Returns:
            bool: If this object is currently running in a process.
        """
        try:
            return self.process.is_alive()
        except AttributeError:
            return False

    # Process
    def construct_process(self) -> None:
        """Creates a separate process for this task."""
        self.process = Process(name=self.name, daemon=self._daemon)

    # Execution
    async def execute_awaitable_future(self, awaitable: Any, future: PipeFuture) -> None:
        future.set_result(await awaitable)

    async def execute_method(self, name, args=(), kwargs={}) -> Any:
        # Get Method from Wrapped Object
        method = getattr(self.object, name, None)

        # Check if the output is an attribute or a callable
        if callable(method):
            # Try Executing Method
            try:
                result = method(*args, **kwargs)
            except Exception as e:
                result = e

            # Create Future if Coroutine
            if iscoroutine(method):
                # Run Coroutine as a Task once
                task = create_task(result)
                await sleep(0)
                # Check if Task is done, returning the result otherwise, return a future.
                if task.done():
                    result = task.result()
                else:
                    future = PipeFuture()
                    self.futures.append(create_task(self.execute_awaitable_future(awaitable=task, future=future)))
                    result = future
        else:
            result = method

        return result

    async def queue_execute_remote(self, name, args=(), kwargs={}) -> PipeFuture:
        future = PipeFuture()
        self.send_queue.put((future, name, args, kwargs))
        return future

    async def execute_remote(self, name, args=(), kwargs={}) -> Any:
        return await self.queue_execute_remote(name, args, kwargs)

    # Listening
    async def listen(self):
        # Listen for Execution Method
        item = await self.send_queue.get_async()
        if item is not None:
            future, name, args, kwargs = item

            # Execute Method
            future.set_result(await self.execute_method(name, args, kwargs))

    async def listen_loop(self) -> None:
        """An async loop that executes the listen consecutively until an event stops it."""
        while self.loop_event.is_set():
            try:
                await create_task(self.listen())
            except InterruptedError as e:
                warn("TaskBlock interrupted, if intentional, handle in the task.")

    # Run Once
    async def _run(self) -> None:
        """Executes a single run of listen."""
        # Flag On
        self._alive_event.set()

        # Run
        await self.listen()

        # Wait for any remaining Futures
        for future in self.futures:
            await future

        # Flag Off
        self._alive_event.clear()

    def _run_async_loop(self) -> None:
        """Executes a single run in the async loop."""
        run(self._run())

    def run(self, obj=None, is_process: bool | None = None) -> Task | None:
        """Executes a single run of the task and delegates to another process is selected.

        Args:
            is_process: Determines if this object should run in a separate process.
        """
        # Raise Error if the task is already running.
        if self._alive_event.is_set():
            raise RuntimeError(f"{self} task is already running.")

        # Set separate process
        if is_process is not None:
            self._is_process = is_process

        # Set object
        if obj is not None:
            self.object = obj

        # Set to Alive
        self._alive_event.set()

        # Use Correct Context
        if self._is_process:
            self.process.target = self._run_async_loop
            self.process.start()
        elif self.event_loop is not None:
            return create_task(self._run())
        else:
            self._run_async_loop()

    # Start Loop
    async def _start(self) -> None:
        """Starts the continuous execution of the task."""
        # Flag On
        self._alive_event.set()
        self.loop_event.set()

        # Loop TaskBlock
        await self.listen_loop()

        # Wait for any remaining Futures
        for future in self.futures:
            await future

        # Flag Off
        self._alive_event.clear()

    def _start_async_loop(self) -> None:
        """Starts the continuous execution of the task in the async loop."""
        run(self._start())

    def start(self, obj: Any =None, is_process: bool | None = None) -> Task | None:
        """Starts the continuous execution of the task and delegates to another process is selected.

        Args:
            is_process: Determines if this object should start in a separate process.
        """
        # Raise Error if the task is already running.
        if self._alive_event.is_set():
            raise RuntimeError(f"{self} task is already running.")

        # Set separate process
        if is_process is not None:
            self._is_process = is_process

        # Set object
        if obj is not None:
            self.object = obj

        # Set to Alive
        self._alive_event.set()

        # Use Correct Context
        if self._is_process:
            self.process.target = self._start_async_loop
            self.process.start()
        elif self.event_loop is not None:
            return create_task(self._start())
        else:
            self._start_async_loop()

    # Joins
    def join(self, timeout: float | None = None) -> None:
        """Wait until this object terminates.

        Args:
            timeout: The time, in seconds, to wait for termination.
        """
        if self.is_process:
            self.process.join(timeout=timeout)
        else:
            self._alive_event.hold(timeout=timeout)

    async def join_async(
        self,
        timeout: float | None = None,
        interval: float = 0.0,
    ) -> None:
        """Asynchronously wait until this object terminates.

        Args:
            timeout: The time, in seconds, to wait for termination.
            interval: The time, in seconds, between each join check.
        """
        if self.is_process:
            await self.process.join_async(timeout=timeout, interval=interval)
        else:
            await self._alive_event.hold_async(timeout=timeout, interval=interval)

    def join_async_task(
        self,
        timeout: float | None = None,
        interval: float = 0.0,
    ) -> Task:
        """Creates waiting for this object to terminate as an asyncio task.

        Args:
            timeout: The time, in seconds, to wait for termination.
            interval: The time, in seconds, between each join check.
        """
        return create_task(self.join_async(timeout=timeout, interval=interval))

    def stop(self) -> None:
        """Abstract method that should stop this task."""
        self.loop_event.clear()

    def terminate(self) -> None:
        """Terminates the current running task, be unsafe for inputs and outputs."""
        self.loop_event.clear()
        self.inputs.interrupt_all()
        self.outputs.interrupt_all()
