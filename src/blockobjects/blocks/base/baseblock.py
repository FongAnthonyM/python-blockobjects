""" baseblock.py.py

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
from asyncio import run, Future, Task, create_task, run_coroutine_threadsafe, iscoroutinefunction
from asyncio.events import AbstractEventLoop, get_event_loop
from abc import abstractmethod
from collections.abc import Iterable
from typing import ClassVar, Any
from warnings import warn

# Third-Party Packages #
from baseobjects.functions import MethodMultiplexer
from ...process import ProcessDelegate

# Local Packages #
from ...io import IOManager


# Definitions #
# Classes #
class BaseBlock(ProcessDelegate):
    """An abstract class which defines an Operation, an easily definable data processing block with inputs and outputs.

    In subclasses the "evaluate" method must be defined as it is data processing element of this object. Additionally,
    the "input_names" and "output_names" must be defined to ensure the IO is mapped properly. "input_names" must match
    the keyword arguments of the "evaluate" method. "output_names" are names for each of the elements of the outputs
    tuple of the "evaluate" method.

    "evaluate" can be called directly which will run without using the Operation IO. This is useful for processing data
    without using the Object IO architecture.

    To use the Object IO architecture "execute" should be called. "execute" first gets the inputs from the inputs
    manager and passes it to "evaluate" method. After evaluating, the output from "evaluate" is then put into the
    outputs manager to be used later.

    "execute" is also MethodMultiplexer, meaning that its call is delegated to different specified method. This gives
    Operation the flexibility to change the "execute" method's implementation during runtime.

    Class Attributes:
        default_execute: The default name of the method to use for execution.
        default_input_names: The default ordered tuple with the names of the inputs to an Operation.
        default_output_names: The default ordered tuple with the names of the outputs to an Operation.

    Attributes:
        inputs: The inputs manager of the Operation.
        outputs: The outputs manager of the Operation.
        execute: The method multiplexer which manages which execute method to run when called.
        input_names: The ordered tuple with the names of the inputs to an Operation.
        _output_names: The ordered tuple with the names of the outputs to an Operation.

    Args:
        *args: Arguments for inheritance.
        init_io: Determines if construct_io run during this construction.
        sets_up: Determines if setup will run during this construction.
        setup_kwargs: The keyword arguments for the setup method.
        init: Determines if this object will construct.
        **kwargs: Keyword arguments for inheritance.
    """
    # Class Attributes #
    default_input_names: ClassVar[tuple[str, ...]] = ()
    default_output_names: ClassVar[tuple[str, ...]] = ()

    # Attributes #
    async_event_loop: AbstractEventLoop
    will_proxy: bool = False

    inputs: IOManager
    outputs: IOManager

    sets_up: bool = True
    tears_down: bool = True

    setup_kwargs: dict[str, Any]
    evaluate_kwargs: dict[str, Any]
    teardown_kwargs: dict[str, Any]

    _setup: MethodMultiplexer
    _task: MethodMultiplexer
    _teardown: MethodMultiplexer

    execute: MethodMultiplexer

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        *args: Any,
        init_io: bool = True,
        sets_up: bool = True,
        setup_kwargs: dict[str, Any] | None = None,
        init: bool = True,
        **kwargs: Any,
    ) -> None:
        # New Attributes #
        self.async_event_loop = get_event_loop()

        self.inputs = IOManager()
        self.outputs = IOManager()

        self.execute = MethodMultiplexer(instance=self, select=self.default_execute)

        # Parent Attributes #
        super().__init__(*args, init=False, **kwargs)

        # Construct #
        if init:
            self.construct(*args, init_io=init_io, sets_up=sets_up, setup_kwargs=setup_kwargs, **kwargs)

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        *args: Any,
        init_io: bool = True,
        sets_up: bool = True,
        setup_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Constructs this object.

        Args:
            *args: Arguments for inheritance.
            init_io: Determines if construct_io run during this construction.
            sets_up: Determines if setup will run during this construction.
            setup_kwargs: The keyword arguments for the setup method.
            **kwargs: Keyword arguments for inheritance.
        """
        # New Assignment #
        self.setup_kwargs = setup_kwargs

        # Construct Parent #
        super().construct(*args, **kwargs)

        if init_io:
            self.construct_io()

        if sets_up:
            self.setup(**({} if setup_kwargs is None else setup_kwargs))

    # State
    def is_executing(self) -> bool:
        """Checks if this object is currently running.

        Returns:
            bool: If this object is currently running.
        """
        return self._executing_event.is_set()

    # IO
    def construct_io(
        self,
        input_names: str | Iterable[str] | None = None,
        output_names: str | Iterable[str] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Constructs the io for this object.

        Args:
            input_names: The names of the inputs to create.
            output_names: The names of the outputs to create.
            *args: The arguments for constructing the io.
            **kwargs: The keyword arguments for constructing the io.
        """
        if input_names is None:
            input_names = self.default_input_names
        if output_names is None:
            output_names = self.default_output_names

        self.inputs.create_io(names=input_names, *args, **kwargs)
        self.outputs.create_io(names=output_names, *args, **kwargs)

        match len(self.outputs.order):
            case 0:
                self.execute.select("execute_no_outputs")
            case 1:
                self.execute.select("execute_one_output")
            case _:
                self.execute.select("execute_multiple_outputs")

    # Setup
    def setup(self, *args: Any, **kwargs: Any) -> None:
        """A method for setting up the object."""
        pass

    async def setup_async(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously runs the setup."""
        if iscoroutinefunction(self.setup):
            await self.setup(*args, **(self.setup_kwargs | kwargs))
        else:
            self.setup(*args, **(self.setup_kwargs | kwargs))

    # Evaluate
    @abstractmethod
    def evaluate(self, *args, **kwargs: Any) -> Any:
        """An abstract method which is the evaluation of this object.

        Args:
            *args: The arguments for evaluating.
            **kwargs: The keyword arguments for evaluating.

        Returns:
            The result of the evaluation.
        """

    async def evaluate_async(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously runs the teardown."""
        if iscoroutinefunction(self.evaluate):
            await self.evaluate(*args, **(self.teardown_kwargs | kwargs))
        else:
            self.evaluate(*args, **(self.teardown_kwargs | kwargs))

    async def evaluate_loop(self, *args: Any, **kwargs: Any) -> None:
        """An async loop that executes evaluate consecutively until an event stops it."""
        # Get the correct method
        evaluate_method = self.evaluate if iscoroutinefunction(self.evaluate) else self.evaluate_async

        # Loop the evaluation
        while self.loop_evaluation.is_set():
            try:
                await create_task(evaluate_method(*args, **kwargs))
            except InterruptedError:
                warn("TaskBlock interrupted, if intentional, handle in the task.")

    # Execute
    def execute_no_output(self) -> None:
        """Evaluates from the inputs and does not output."""
        self.evaluate(**self.inputs.get_all())

    def execute_one_output(self) -> None:
        """Evaluates from the inputs and puts the single result to the outputs."""
        self.outputs.put_ordered((self.evaluate(**self.inputs.get_all()),))

    def execute_multiple_outputs(self) -> None:
        """Evaluates from the inputs and puts the multiple results to the outputs."""
        self.outputs.put_ordered(self.evaluate(**self.inputs.get_all()))

    def execute_dict_output(self) -> None:
        """Evaluates from the inputs and puts the output dict directly to the outputs."""
        self.outputs.put_all(self.evaluate(**self.inputs.get_all()))

    async def execution_loop(self, *args: Any, **kwargs: Any) -> None:
        """An async loop that executes evaluate consecutively until an event stops it."""
        # Get the correct method
        evaluate_method = self.evaluate if iscoroutinefunction(self.evaluate) else self.evaluate_async

        # Loop the evaluation
        while self.loop_evaluation.is_set():
            try:
                await create_task(evaluate_method(*args, **kwargs))
            except InterruptedError:
                warn("TaskBlock interrupted, if intentional, handle in the task.")

    # Teardown
    def teardown(self, *args: Any, **kwargs: Any) -> None:
        """A method for tearing down the object."""
        pass

    async def teardown_async(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously runs the teardown."""
        if iscoroutinefunction(self.teardown):
            await self.teardown(*args, **(self.teardown_kwargs | kwargs))
        else:
            self.teardown(*args, **(self.teardown_kwargs | kwargs))

    # Run Block Once
    async def _run(
        self,
        s_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
        d_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Executes a single run of the task.

        Args:
            s_kwargs: The keyword arguments for task setup.
            t_kwargs: The keyword arguments for the task.
            d_kwargs: The keyword arguments for task teardown.
        """
        # Flag On
        self._alive_event.set()

        # Optionally Setup
        if self.sets_up:
            await self.setup_async(**(s_kwargs or {}))

        # Run TaskBlock
        if self._task.is_coroutine:
            await self._task(**(self.task_kwargs | (t_kwargs or {})))
        else:
            await self.task_async(**(self.task_kwargs | (t_kwargs or {})))

        # Optionally Teardown
        if self.tears_down:
            await self.teardown_async(**(d_kwargs or {}))

        # Wait for any remaining Futures
        for future in self.futures:
            await future

        # Flag Off
        self._alive_event.clear()

    def _run_async_loop(
        self,
        s_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
        d_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Executes a single run of the task.

        Args:
            s_kwargs: The keyword arguments for task setup.
            t_kwargs: The keyword arguments for the task.
            d_kwargs: The keyword arguments for task teardown.
        """
        run(self._run(s_kwargs=s_kwargs, t_kwargs=t_kwargs, d_kwargs=d_kwargs))

    async def run_async(
        self,
        is_process: bool | None = None,
        s_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
        d_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Executes a single async run of the task and delegates to another process is selected.

        Args:
            is_process: Determines if this object should run in a separate process.
            s_kwargs: The keyword arguments for task setup.
            t_kwargs: The keyword arguments for the task.
            d_kwargs: The keyword arguments for task teardown.
        """
        # Raise Error if the task is already running.
        if self._alive_event.is_set():
            raise RuntimeError(f"{self} task is already running.")

        # Set to Alive
        self._alive_event.set()

        # Set separate process
        if is_process is not None:
            self._is_process = is_process

        # Use Correct Context
        if self._is_process:
            self.process.target = self._run_async_loop
            self.process.kwargs = {"s_kwargs": s_kwargs, "t_kwargs": t_kwargs, "d_kwargs": d_kwargs}
            self.process.start()
        else:
            await self._run(s_kwargs, t_kwargs, d_kwargs)

    def run(
        self,
        as_proxy: bool | None = None,
        s_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
        d_kwargs: dict[str, Any] | None = None,
    ) -> Future | None:
        """Executes a single run of the task and delegates to another process is selected.

        Args:
            as_proxy: Determines if this object should run in a separate process.
            s_kwargs: The keyword arguments for task setup.
            t_kwargs: The keyword arguments for the task.
            d_kwargs: The keyword arguments for task teardown.
        """
        # Raise Error if the task is already running.
        if self._alive_event.is_set():
            raise RuntimeError(f"{self} is already executing.")

        # Set to Alive
        self._alive_event.set()

        # Run as Proxy
        if as_proxy or (as_proxy is None and self.will_proxy):
            if not self.is_alive():
                self._start_server()
            self._proxy.run()
        elif self.async_event_loop.is_running():
            return run_coroutine_threadsafe(self._run(s_kwargs, t_kwargs, d_kwargs), self.async_event_loop)
        else:
            self._run_async_loop(s_kwargs, t_kwargs, d_kwargs)

    # Start Block Loop
    async def _start(
        self,
        s_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
        d_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Starts the continuous execution of the task.

        Args:
            s_kwargs: The keyword arguments for task setup.
            t_kwargs: The keyword arguments for the task.
            d_kwargs: The keyword arguments for task teardown.
        """
        # Flag On
        self._alive_event.set()
        self.loop_event.set()

        # Optionally Setup
        if self.sets_up:
            await self.setup_async(**(s_kwargs or {}))

        # Loop TaskBlock
        await self.loop_task(**(self.task_kwargs | (t_kwargs or {})))

        # Optionally Teardown
        if self.tears_down:
            await self.teardown_async(**(d_kwargs or {}))

        # Wait for any remaining Futures
        for future in self.futures:
            await future

        # Flag Off
        self._alive_event.clear()

    def _start_async_loop(
        self,
        s_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
        d_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Starts the continuous execution of the task in an async run.

        Args:
            s_kwargs: The keyword arguments for task setup.
            t_kwargs: The keyword arguments for the task.
            d_kwargs: The keyword arguments for task teardown.
        """
        run(self._start(s_kwargs=s_kwargs, t_kwargs=t_kwargs, d_kwargs=d_kwargs))

    async def start_async(
        self,
        is_process: bool | None = None,
        s_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
        d_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Starts the async continuous execution of the task and delegates to another process is selected.

        Args:
            is_process: Determines if this object should start in a separate process.
            s_kwargs: The keyword arguments for task setup.
            t_kwargs: The keyword arguments for the task.
            d_kwargs: The keyword arguments for task teardown.
        """
        # Raise Error if the task is already running.
        if self._alive_event.is_set():
            raise RuntimeError(f"{self} task is already running.")

        # Set to Alive
        self._alive_event.set()

        # Set separate process
        if is_process is not None:
            self._is_process = is_process

        # Use Correct Context
        if self._is_process:
            self.process.target = self._start_async_loop
            self.process.kwargs = {"s_kwargs": s_kwargs, "t_kwargs": t_kwargs, "d_kwargs": d_kwargs}
            self.process.start()
        else:
            await self._start(s_kwargs, t_kwargs, d_kwargs)

    def start(
        self,
        is_process: bool | None = None,
        s_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
        d_kwargs: dict[str, Any] | None = None,
    ) -> Task | None:
        """Starts the continuous execution of the task and delegates to another process is selected.

        Args:
            is_process: Determines if this object should start in a separate process.
            s_kwargs: The keyword arguments for task setup.
            t_kwargs: The keyword arguments for the task.
            d_kwargs: The keyword arguments for task teardown.
        """
        # Raise Error if the task is already running.
        if self._alive_event.is_set():
            raise RuntimeError(f"{self} task is already running.")

        # Set to Alive
        self._alive_event.set()

        # Set separate process
        if is_process is not None:
            self._is_process = is_process

        # Use Correct Context
        if self._is_process:
            self.process.target = self._start_async_loop
            self.process.kwargs = {"s_kwargs": s_kwargs, "t_kwargs": t_kwargs, "d_kwargs": d_kwargs}
            self.process.start()
            return
        elif self.async_event_loop is not None:
            return create_task(self._start(s_kwargs, t_kwargs, d_kwargs))
        else:
            self._start_async_loop(s_kwargs, t_kwargs, d_kwargs)
            return
