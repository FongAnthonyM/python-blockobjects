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
from asyncio import run, Future, Task, create_task, run_coroutine_threadsafe, iscoroutinefunction, sleep
from asyncio.events import AbstractEventLoop, get_event_loop
from abc import abstractmethod
from collections.abc import Iterable
from concurrent.futures import Future as ConcurrentFuture
from contextlib import contextmanager
from time import perf_counter
from typing import ClassVar, Any
from warnings import warn

# Third-Party Packages #
from baseobjects.functions import CallableMultiplexObject, MethodMultiplexer
from ...process import ProcessDelegate
from ...process.context import ContextualEvent

# Local Packages #
from ...io import IOManager


# Definitions #
# Classes #
class BaseBlock(ProcessDelegate, CallableMultiplexObject):
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
    public_exposed = False
    exposed: ClassVar[set] = {"run", "start"}

    default_input_names: ClassVar[tuple[str, ...]] = ()
    default_required_input: ClassVar[tuple[str, ...]] = ()
    default_optional_input: ClassVar[dict[str, Any]] = {}
    default_output_names: ClassVar[tuple[str, ...]] = ()

    init_setup: ClassVar[bool] = True

    # Attributes #
    # Backend
    untransmittable = {"loop_event", "inputs", "outputs", "futures"}
    async_event_loop: AbstractEventLoop

    # State
    loop_event: ContextualEvent
    will_proxy: bool = False
    _is_executing: bool = False

    # IO
    inputs: IOManager
    outputs: IOManager

    format_output: MethodMultiplexer

    # Setup/Evaluate/Teardown
    sets_up: bool = True
    tears_down: bool = True

    setup_kwargs: dict[str, Any] = {}
    evaluate_kwargs: dict[str, Any] = {}
    teardown_kwargs: dict[str, Any] = {}

    _setup: MethodMultiplexer
    _evaluate: MethodMultiplexer
    _teardown: MethodMultiplexer

    execute_input: MethodMultiplexer
    execute_input_async: MethodMultiplexer
    execute_output: MethodMultiplexer
    execute_output_async: MethodMultiplexer

    futures: list[Future]

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        *args: Any,
        will_proxy: bool | None = None,
        init_io: bool = True,
        init_setup: bool | None = None,
        setup_kwargs: dict[str, Any] | None = None,
        init: bool = True,
        **kwargs: Any,
    ) -> None:
        # New Attributes #
        self.async_event_loop = get_event_loop()
        self.loop_event = ContextualEvent()

        self.inputs = IOManager()
        self.outputs = IOManager()
        self.format_output = MethodMultiplexer(instance=self)

        self.setup_kwargs = self.setup_kwargs.copy()
        self.evaluate_kwargs = self.evaluate_kwargs.copy()
        self.teardown_kwargs = self.teardown_kwargs.copy()

        self.execute_input = MethodMultiplexer(instance=self)
        self.execute_input_async = MethodMultiplexer(instance=self)
        self.execute_output = MethodMultiplexer(instance=self)
        self.execute_output_async = MethodMultiplexer(instance=self)

        self.futures = []

        # Parent Attributes #
        super().__init__(*args, init=False, **kwargs)

        # Construct #
        if init:
            self.construct(
                *args,
                will_proxy=will_proxy,
                init_io=init_io,
                init_setup=init_setup,
                setup_kwargs=setup_kwargs,
                **kwargs,
            )

    # Pickling
    def __getstate__(self) -> dict[str, Any]:
        """Creates a dictionary of attributes which can be used to rebuild this object.

        Returns:
            A dictionary of this object's attributes.
        """
        state = super().__getstate__()
        for name in {"will_proxy", "async_event_loop"}:
            if name in state:
                del state[name]
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Builds this object based on a dictionary of corresponding attributes.

        Args:
            state: The attributes to build this object from.
        """
        super().__setstate__(state)
        self.async_event_loop = get_event_loop()

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        *args: Any,
        will_proxy: bool | None = None,
        init_io: bool = True,
        init_setup: bool | None = None,
        setup_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Constructs this object.

        Args:
            *args: Arguments for inheritance.
            will_proxy: Determines if this object will execute as proxy.
            init_io: Determines if construct_io run during this construction.
            init_setup: Determines if setup will run during this construction.
            setup_kwargs: The keyword arguments for the setup method.
            **kwargs: Keyword arguments for inheritance.
        """
        # New Assignment #
        if will_proxy is not None:
            self.will_proxy = will_proxy

        if setup_kwargs is not None:
            self.setup_kwargs.update(setup_kwargs)

        if init_io:
            self.construct_io()

        if init_setup or (init_setup is None and self.init_setup):
            self.setup(**({} if setup_kwargs is None else setup_kwargs))

        # Construct Parent #
        super().construct(*args, **kwargs)

    # State
    def is_executing(self) -> bool:
        """Checks if this object is currently running.

        Returns:
            bool: If this object is currently running.
        """
        return self._is_executing

    @contextmanager
    def _executing_context_manager(self) -> None:
        try:
            self._is_executing = True
            yield None
        finally:
            self._is_executing = False

    # IO
    def one_output(self, output) -> tuple:
        """Formats an output if was the only output of the block."""
        return (output,)

    def multiple_outputs(self, output) -> None:
        """Formats the outputs if of the block."""
        return output

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

        self.inputs.create_io(name=input_names, *args, **kwargs)
        self.outputs.create_io(name=output_names, *args, **kwargs)

        self.inputs.required = self.default_required_input
        self.inputs.optional_defaults.update(self.default_optional_input)

        match len(self.inputs):
            case 0:
                self.execute_input.select("_execute_no_input")
                self.execute_input_async.select("_execute_no_input_async")
            case _:
                self.execute_input.select("_execute_input")
                self.execute_input_async.select("_execute_input_async")

        match len(self.outputs.order):
            case 0:
                self.execute_output.select("_execute_no_output")
                self.execute_output_async.select("_execute_no_output_async")
                self.format_output.select("multiple_outputs")
            case 1:
                self.execute_output.select("_execute_one_output")
                self.execute_output_async.select("_execute_one_output_async")
                self.format_output.select("one_output")
            case _:
                self.execute_output.select("_execute_multiple_outputs")
                self.execute_output_async.select("_execute_multiple_outputs_async")
                self.format_output.select("multiple_outputs")

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

    async def evaluate_async(self, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously runs the teardown."""
        if iscoroutinefunction(self.evaluate):
            return await self.evaluate(*args, **(self.teardown_kwargs | kwargs))
        else:
            return self.evaluate(*args, **(self.teardown_kwargs | kwargs))

    # Execute IO
    async def _execute_no_input(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {}

    async def _execute_no_input_async(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {}

    def _execute_input(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.inputs.get(*args, **kwargs)

    async def _execute_input_async(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return await self.inputs.get_async(*args, **kwargs)

    def _execute_no_output(self, *args: Any, **kwargs: Any) -> None:
        """Executes no output."""

    async def _execute_no_output_async(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously executes no output."""

    def _execute_one_output(self, output, *args: Any, **kwargs: Any) -> None:
        """Executes one output."""
        self.outputs.put_ordered((output,), *args, **kwargs)

    async def _execute_one_output_async(self, output, *args: Any, **kwargs: Any) -> None:
        """Asynchronously executes one output."""
        await self.outputs.put_ordered_async((output,), *args, **kwargs)

    def _execute_multiple_outputs(self, output, *args: Any, **kwargs: Any) -> None:
        """Evaluates from the inputs and puts the multiple results to the outputs."""
        self.outputs.put_ordered(output, *args, **kwargs)

    async def _execute_multiple_outputs_async(self, output, *args: Any, **kwargs: Any) -> None:
        """Evaluates from the inputs and puts the multiple results to the outputs."""
        await self.outputs.put_ordered_async(output, *args, **kwargs)

    def _execute_dict_output(self, output, **kwargs: Any) -> None:
        """Evaluates from the inputs and puts the output dict directly to the outputs."""
        self.outputs.put_all(output, **kwargs)

    async def _execute_dict_output_async(self, output, **kwargs: Any) -> None:
        """Evaluates from the inputs and puts the output dict directly to the outputs."""
        await self.outputs.put_all_async(output, **kwargs)

    # Execute
    def _execute(self, *args: Any, **kwargs: Any) -> None:
        self.execute_output(self.evaluate(**self.execute_input()))

    def execute(self, *args: Any, **kwargs: Any) -> None:
        with self._executing_context_manager():
            self._execute(*args, **kwargs)

    async def _execute_async(self, *args: Any, **kwargs: Any) -> None:
        evaluate_method = self.evaluate if iscoroutinefunction(self.evaluate) else self.evaluate_async
        await self.execute_output_async(await evaluate_method(**await self.execute_input_async()))

    async def execute_async(self, *args: Any, **kwargs: Any) -> None:
        with self._executing_context_manager():
            await self._execute_async(*args, **kwargs)

    def _execution_loop(self, *args: Any, **kwargs: Any) -> None:
        while self.loop_event.is_set():
            # Get Inputs
            inputs = self.execute_input_async()
            if any((inputs[n]) for n in self.inputs.required):
                self.loop_event.clear()
                continue

            # Evaluate
            output = self.evaluate(**inputs)

            # Outputs
            self.execute_output_async(output)

    async def _execution_loop_async(self, *args: Any, **kwargs: Any) -> None:
        """An async loop that executes evaluate consecutively until an event stops it."""
        # Get the correct method
        evaluate_method = self.evaluate if iscoroutinefunction(self.evaluate) else self.evaluate_async

        # Loop the evaluation
        while self.loop_event.is_set():
            # Get Inputs
            inputs = await create_task(self.execute_input_async())
            if any((self.inputs.break_sentinel == inputs[n]) for n in self.inputs.required):
                self.loop_event.clear()
                continue

            # Evaluate
            output = await create_task(evaluate_method(**inputs))

            # Outputs
            await create_task(self.execute_output_async(output))

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
        e_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Runs a single execution of the block.

        Args:
            s_kwargs: The keyword arguments for block setup.
            e_kwargs: The keyword arguments for block execution.
            t_kwargs: The keyword arguments for block teardown.
        """
        # Flag On
        with self._executing_context_manager():
            # Optionally Setup
            if self.sets_up:
                await self.setup_async(**(s_kwargs or {}))

            # Run one Execution
            await self._execute_async(**(e_kwargs or {}))

            # Optionally Teardown
            if self.tears_down:
                await self.teardown_async(**(t_kwargs or {}))

            # Wait for any remaining Futures
            for future in self.futures:
                await future

    def _run_async_loop(
        self,
        s_kwargs: dict[str, Any] | None = None,
        e_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Runs a single execution of the block using the async event loop.

        Args:
            s_kwargs: The keyword arguments for block setup.
            e_kwargs: The keyword arguments for block execution.
            t_kwargs: The keyword arguments for block teardown.
        """
        run(self._run(s_kwargs, e_kwargs, t_kwargs))

    def run(
        self,
        as_proxy: bool | None = None,
        s_kwargs: dict[str, Any] | None = None,
        e_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
    ) -> Future | None:
        """Runs a single execution of the block, delegating to another process if selected.

        Args:
            as_proxy: Determines if this object should run in a separate process.
            s_kwargs: The keyword arguments for block setup.
            e_kwargs: The keyword arguments for block execution.
            t_kwargs: The keyword arguments for block teardown.
        """
        # Raise Error if the task is already running.
        if self.is_executing():
            raise RuntimeError(f"{self} task is already running.")

        # Run as Proxy
        if as_proxy or (as_proxy is None and self.will_proxy):
            if not self.is_alive():
                self._start_server()
            self._proxy.run(s_kwargs, e_kwargs, t_kwargs)
        elif self.async_event_loop.is_running():
            return run_coroutine_threadsafe(self._run(s_kwargs, e_kwargs, t_kwargs), self.async_event_loop)
        else:
            self._run_async_loop(s_kwargs, e_kwargs, t_kwargs)

    async def run_async(
        self,
        as_proxy: bool | None = None,
        s_kwargs: dict[str, Any] | None = None,
        e_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Asynchronously runs a single execution of the block, delegating to another process if selected.

        Args:
            as_proxy: Determines if this object should run in a separate process.
            s_kwargs: The keyword arguments for block setup.
            e_kwargs: The keyword arguments for block execution.
            t_kwargs: The keyword arguments for block teardown.
        """
        # Raise Error if the task is already running.
        if self.is_executing():
            raise RuntimeError(f"{self} task is already running.")

        # Use Correct Context
        if as_proxy or (as_proxy is None and self.will_proxy):
            if not self.is_alive():
                self._start_server()
            await self._proxy.run_async(s_kwargs, e_kwargs, t_kwargs)
        else:
            await self._run(s_kwargs, e_kwargs, t_kwargs)

    # Start Block Continuous
    async def _start(
        self,
        s_kwargs: dict[str, Any] | None = None,
        e_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Starts the continuous execution of the block.

        Args:
            s_kwargs: The keyword arguments for block setup.
            e_kwargs: The keyword arguments for block execution.
            t_kwargs: The keyword arguments for block teardown.
        """
        # Flag On
        with self._executing_context_manager():
            self.loop_event.set()

            # Optionally Setup
            if self.sets_up:
                await self.setup_async(**(s_kwargs or {}))

            # Loop TaskBlock
            await self._execution_loop_async(**(e_kwargs or {}))

            # Optionally Teardown
            if self.tears_down:
                await self.teardown_async(**(t_kwargs or {}))

            # Wait for any remaining Futures
            for future in self.futures:
                await future

    def _start_async_loop(
        self,
        s_kwargs: dict[str, Any] | None = None,
        e_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Starts the continuous execution of the block in an async run.

        Args:
            s_kwargs: The keyword arguments for block setup.
            e_kwargs: The keyword arguments for block execution.
            t_kwargs: The keyword arguments for block teardown.
        """
        run(self._start(s_kwargs, e_kwargs, t_kwargs))

    def start(
        self,
        as_proxy: bool | None = None,
        s_kwargs: dict[str, Any] | None = None,
        e_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
    ) -> Future | None:
        """Starts the continuous execution of the block, delegating to another process if selected.

        Args:
            as_proxy: Determines if this object should run in a separate process.
            s_kwargs: The keyword arguments for block setup.
            e_kwargs: The keyword arguments for block execution.
            t_kwargs: The keyword arguments for block teardown.
        """
        # Raise Error if the task is already running.
        if self.is_executing():
            raise RuntimeError(f"{self} task is already running.")

        # Run as Proxy
        if as_proxy or (as_proxy is None and self.will_proxy):
            if not self.is_alive():
                self._start_server()
            self._proxy.start(s_kwargs, e_kwargs, t_kwargs)
        elif self.async_event_loop.is_running():
            return run_coroutine_threadsafe(self._start(s_kwargs, e_kwargs, t_kwargs), self.async_event_loop)
        else:
            self._start_async_loop(s_kwargs, e_kwargs, t_kwargs)

    async def start_async(
        self,
        as_proxy: bool | None = None,
        s_kwargs: dict[str, Any] | None = None,
        e_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Asynchronously starts the continuous execution of the block, delegating to another process if selected.

        Args:
            as_proxy: Determines if this object should run in a separate process.
            s_kwargs: The keyword arguments for block setup.
            e_kwargs: The keyword arguments for block execution.
            t_kwargs: The keyword arguments for block teardown.
        """
        # Raise Error if the task is already running.
        if self.is_executing():
            raise RuntimeError(f"{self} task is already running.")

        # Use Correct Context
        if as_proxy or (as_proxy is None and self.will_proxy):
            if not self.is_alive():
                self._start_server()
            await self._proxy.start_async(s_kwargs, e_kwargs, t_kwargs)
        else:
            await self._start(s_kwargs, e_kwargs, t_kwargs)

    # Join Execution
    def _join_execution(self, timeout: float | None = None) -> None:
        """Waits until the execution of the block has finished.

        Args:
            timeout: The time, in seconds, to wait for the block to finish.
        """
        if timeout is None:
            while self._is_executing:
                pass
        else:
            deadline = perf_counter() + timeout
            while self._is_executing:
                if deadline <= perf_counter():
                    return

    def join_execution(self, timeout: float | None = None) -> None:
        """Waits until the execution of the block has finished.

        Args:
            timeout: The time, in seconds, to wait for the block to finish.
        """
        self._join_execution(timeout)

    async def _join_execution_async(self, timeout: float | None = None, interval: float = 0.0) -> None:
        """Asynchronously waits until the execution of the block has finished.

        Args:
            timeout: The time, in seconds, to wait for the block to finish.
            interval: The time, in seconds, between each join check.
        """
        if timeout is None:
            while self._is_executing:
                await sleep(interval)
        else:
            deadline = perf_counter() + timeout
            while self._is_executing:
                if deadline <= perf_counter():
                    return
                await sleep(interval)

    async def join_execution_async(self, timeout: float | None = None, interval: float = 0.0) -> None:
        """Asynchronously waits until the execution of the block has finished.

        Args:
            timeout: The time, in seconds, to wait for the block to finish.
            interval: The time, in seconds, between each join check.
        """
        await self._join_execution_async(timeout, interval)

    # Stop Block Continuous Execution
    def stop(self, server: bool = True, update: bool = True) -> None:
        """Stops the execution of this block, optionally stopping the server relative to this object.

        Args:
            server: Determines if the remote server should be stopped.
            update: Determines if this object should be updated from the server before stopping.
        """
        self.loop_event.clear()
        self.inputs.put_break_sentinel()
        if self.is_alive() and server:
            if update:
                self.join_execution()
            self._stop_server(update)

    async def stop_async(self, server: bool = True, update: bool = True) -> None:
        """Asynchronously Stops the execution of this block, optionally stopping the server relative to this object.

        Args:
            server: Determines if the remote server should be stopped.
            update: Determines if this object should be updated from the server before stopping.
        """
        self.loop_event.clear()
        await self.inputs.put_break_sentinel_async()
        if self.is_alive() and server:
            if update:
                await self.join_execution_async()
            self._stop_server(update)

    # Proxy
