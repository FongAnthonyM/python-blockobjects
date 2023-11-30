""" remoteexecutor.py.py

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
from asyncio import run, Future, Task, create_task, iscoroutine
from asyncio.events import AbstractEventLoop, _get_running_loop
from typing import Any
from warnings import warn

# Third-Party Packages #
from baseobjects.functions import CallableMultiplexObject, MethodMultiplexer
from baseobjects import BaseObject

# Local Packages #
from .synchronize import MultiProcessingEvent
from .queues import MultiProcessingQueue
from .process import Process


# Definitions #
# Classes #
class RemoteExecutor(BaseObject):
    """

    Class Attributes:

    Attributes:

    Args:

    """
    # Magic Methods #
    # Construction/Destruction
    def __init__(self,  init: bool = True) -> None:
        # New Attributes #
        self.name: str = ""
        self._is_async: bool = True
        self._is_process: bool = False
        self.sets_up: bool = True
        self.tears_down: bool = True
        self.loop_event: MultiProcessingEvent = MultiProcessingEvent()
        self._alive_event: MultiProcessingEvent = MultiProcessingEvent()
        self.futures: list[Future] = []

        self.send_queue: MultiProcessingQueue = MultiProcessingQueue()
        self.receive_queue: MultiProcessingQueue = MultiProcessingQueue()

        self.object = Any

        self.process: Process | None = Process()
        self._daemon: bool | None = None

        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct()

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

    @property
    def async_event_loop(self) -> AbstractEventLoop | None:
        """The async event loop if it is running otherwise None."""
        return _get_running_loop()

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
    def construct(self, ) -> None:
        super().construct()

    # State Methods
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

    # Listening
    def execute_remote(self, name, args=(), kwargs={}) -> Any:
        self.send_queue.put((name, args, kwargs))
        return self.receive_queue.get()

    async def listen(self):
        item = await self.send_queue.get_async()
        if item is None:
            return

        method = getattr(self.object, item[0], None)

        if callable(method):
            try:
                result = method(*item[1], **item[2])
            except Exception as e:
                result = e
            if iscoroutine(method):
                self.futures.append(result)
                result = None
        else:
            result = method
        self.receive_queue.put(result)

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

    async def run_async(self, obj=None, is_process: bool | None = None) -> None:
        """Executes a single async run and delegates to another process is selected.

        Args:
            is_process: Determines if this object should run in a separate process.
        """
        # Raise Error if the task is already running.
        if self._alive_event.is_set():
            raise RuntimeError(f"{self} task is already running.")

        # Set object
        if obj is not None:
            self.object = obj

        # Set to Alive
        self._alive_event.set()

        # Set separate process
        if is_process is not None:
            self._is_process = is_process

        # Use Correct Context
        if self._is_process:
            self.process.target = self._run_async_loop
            self.process.start()
        else:
            await self._run()

    def run(self, obj=None, is_process: bool | None = None) -> Task | None:
        """Executes a single run of the task and delegates to another process is selected.

        Args:
            is_process: Determines if this object should run in a separate process.
        """
        # Raise Error if the task is already running.
        if self._alive_event.is_set():
            raise RuntimeError(f"{self} task is already running.")

        # Set object
        if obj is not None:
            self.object = obj

        # Set to Alive
        self._alive_event.set()

        # Set separate process
        if is_process is not None:
            self._is_process = is_process

        # Use Correct Context
        if self._is_process:
            self.process.target = self._run_async_loop
            self.process.start()
            return
        elif self.async_event_loop is not None:
            return create_task(self._run())
        else:
            self._run_async_loop()
            return

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

    async def start_async(self, obj=None, is_process: bool | None = None) -> None:
        """Starts the async continuous execution of the task and delegates to another process is selected.

        Args:
            is_process: Determines if this object should start in a separate process.
        """
        # Raise Error if the task is already running.
        if self._alive_event.is_set():
            raise RuntimeError(f"{self} task is already running.")

        # Set object
        if obj is not None:
            self.object = obj

        # Set to Alive
        self._alive_event.set()

        # Set separate process
        if is_process is not None:
            self._is_process = is_process

        # Use Correct Context
        if self._is_process:
            self.process.target = self._start_async_loop
            self.process.start()
        else:
            await self._start()

    def start(self, obj=None, is_process: bool | None = None) -> Task | None:
        """Starts the continuous execution of the task and delegates to another process is selected.

        Args:
            is_process: Determines if this object should start in a separate process.
        """
        # Raise Error if the task is already running.
        if self._alive_event.is_set():
            raise RuntimeError(f"{self} task is already running.")

        # Set object
        if obj is not None:
            self.object = obj

        # Set to Alive
        self._alive_event.set()

        # Set separate process
        if is_process is not None:
            self._is_process = is_process

        # Use Correct Context
        if self._is_process:
            self.process.target = self._start_async_loop
            self.process.start()
            return
        elif self.async_event_loop is not None:
            return create_task(self._start())
        else:
            self._start_async_loop()
            return

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
