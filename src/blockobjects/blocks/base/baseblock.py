""" baseblock.py.py

"""
from multiprocessing.forkserver import set_forkserver_preload

# Package Header #
from ...header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Standard Libraries #
from asyncio import run, gather, Future, Task, create_task, run_coroutine_threadsafe, iscoroutinefunction, wait_for
from asyncio.events import AbstractEventLoop, _get_running_loop
from abc import abstractmethod
from collections.abc import Iterable
from collections import deque
from contextlib import contextmanager
from functools import partial
from itertools import chain
from time import perf_counter
from typing import ClassVar, Any
from uuid import uuid4
from warnings import warn

# Third-Party Packages #
from baseobjects import BaseMethod, SentinelObject
from baseobjects.functions import MethodMultiplexer
from ...process import ProcessArbitrator, arbitratemethod, ProxyInterface
from ...process.context import BaseProcessingContext, ContextualEvent

# Local Packages #
from ...io import IORouter, ArbitratingIOManager, IOArbitratorWrapper, IdentifiedItem
from ...io.containers import IOQueue, IOContextualQueue


# Definitions #
# Classes #
class BaseBlock(ProcessArbitrator):
    """An abstract class which defines a Block, an easily definable data processing block with inputs and outputs.

    In subclasses the "evaluate" method must be defined as it is data processing element of this object. Additionally,
    the "input_names" and "output_names" must be defined to ensure the IO is mapped properly. "input_names" must match
    the keyword arguments of the "evaluate" method. "output_names" are names for each of the elements of the outputs
    tuple of the "evaluate" method.

    "evaluate" can be called directly which will run without using the Block IO. This is useful for processing data
    without using the Object IO architecture.

    Class Attributes:
        default_input_names: The default ordered tuple with the names of the inputs to a Block.
        default_output_names: The default ordered tuple with the names of the outputs to a Block.

    Attributes:
        inputs: The inputs manager of the Block.
        outputs: The outputs manager of the Block.
        input_names: The ordered tuple with the names of the inputs to an Block.
        _output_names: The ordered tuple with the names of the outputs to an Block.

    Args:
        *args: Arguments for inheritance.
        init_io: Determines if construct_io run during this construction.
        sets_up: Determines if setup will run during this construction.
        setup_kwargs: The keyword arguments for the setup method.
        init: Determines if this object will construct.
        **kwargs: Keyword arguments for inheritance.
    """
    # Class Attributes #
    public_exposed: ClassVar[bool] = False
    exposed: ClassVar[set] = {
        "set_inputs_proxy",
        "set_inputs_proxy_async",
        "set_outputs_proxy",
        "set_outputs_proxy_async",
        "finalize_io",
        "finalize_io_async",
        "is_executing",
        "is_loop_event",
        "set_loop_event",
        "clear_loop_event",
        "_produce",
        "_produce_async",
        "run",
        "run_async",
        "start",
        "start_async",
        "stop",
        "stop_async",
        "join_execution",
        "join_execution_async",
    }
    local_methods: ClassVar[set] = {"stop", "stop_block_async"}

    default_input_names: ClassVar[tuple[str, ...]] = ()
    default_required_input: ClassVar[tuple[str, ...] | None] = None
    _default_input_signal_names: ClassVar[tuple[str, ...]] = ("stop_flag",)
    default_input_signal_names: ClassVar[tuple[str, ...]] = ()
    default_optional_input: ClassVar[dict[str, Any]] = {}
    default_output_names: ClassVar[tuple[str, ...]] = ()
    _default_output_signal_names: ClassVar[tuple[str, ...]] = ("done_flag",)
    default_output_signal_names: ClassVar[tuple[str, ...]] = ()

    init_setup: ClassVar[bool] = False

    # Attributes #
    # Backend
    untransmittable = {"loop_event", "inputs", "outputs", "futures"}
    _async_event_loop: AbstractEventLoop | None = None

    # State
    _loop_event: bool = False
    _will_proxy: bool = False
    will_produce: bool = False
    _is_executing: bool = False
    _executing_waiters: deque[Future]
    _name: str = ""
    _has_setup: bool = False
    _has_torndown: bool = False

    # IO
    input_link_name: str = "block_input"

    _output_order: tuple[str, ...] | None = None
    output_as_items: bool = False
    no_output_sentinel: Any = SentinelObject("no_output_sentinel")

    io_wrapper_get_method: str | None = None
    io_wrapper_get_async_method: str | None = None
    io_wrapper_put_method: str | None = "_produce"
    io_wrapper_put_async_method: str | None = "_produce_async"

    inputs: ArbitratingIOManager
    outputs: ArbitratingIOManager

    # IO Signals
    signal_io_name: str = "block_signals"
    signals_type: type[IORouter] = IORouter

    _signal_callback_map_: dict[str, dict[str, str | dict[str, Any]]] = {
        "stop_callback": {"method": "stop_signal", "signals": ("stop_flag",)}
    }
    signal_callback_map: dict[str, dict[str, str | dict[str, Any]]] = {}

    # Setup/Evaluate/Teardown
    setup_kwargs: dict[str, Any] = {}
    evaluate_kwargs: dict[str, Any] = {}
    teardown_kwargs: dict[str, Any] = {}

    _setup: MethodMultiplexer
    _evaluate: MethodMultiplexer
    _teardown: MethodMultiplexer

    _setup_task: Task | None = None
    _evaluate_tasks: deque[Task]
    _teardown_task: Task | None = None
    _production_task: Task | None = None

    stop_flag: bool = False
    stop_task: Task | None = None

    futures: list[Future]

    # Properties
    @property
    def async_event_loop(self) -> AbstractEventLoop:
        if self._async_event_loop is None:
            self.async_event_loop = _get_running_loop()
        return self._async_event_loop

    @async_event_loop.setter
    def async_event_loop(self, value: AbstractEventLoop) -> None:
        self._async_event_loop = value

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value
        self.inputs.name = f"{value}_inputs"
        self.outputs.name = f"{value}_outputs"

    @property
    def will_proxy(self) -> bool:
        return self._will_proxy

    @will_proxy.setter
    def will_proxy(self, value: bool) -> None:
        self._will_proxy = value
        self.inputs.will_proxy = value
        self.outputs.will_proxy = value

    @property
    def is_producing(self) -> bool:
        return self._production_task is not None

    @property
    def input_signals(self) -> IORouter:
        return self.inputs.io_groups["signals"][self.signal_io_name]

    @property
    def output_signals(self) -> IORouter:
        return self.outputs.io_groups["signals"][self.signal_io_name]

    @property
    def output_order(self) -> tuple[str, ...]:
        if self._output_order is None:
            self._output_order = self.outputs.get_order()
        return self._output_order

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        *args: Any,
        name: str | None = None,
        will_proxy: bool | None = None,
        will_produce: bool | None = None,
        init_io: bool = True,
        init_setup: bool | None = None,
        setup_kwargs: dict[str, Any] | None = None,
        start_server: bool = False,
        proxy_context: BaseProcessingContext | None = None,
        _state: dict[str, Any] | None = None,
        init: bool = True,
        **kwargs: Any,
    ) -> None:
        # New Attributes #
        # self.async_event_loop = get_event_loop()
        self._executing_waiters = deque()
        self.signal_callback_map = self._signal_callback_map_ | self.signal_callback_map

        self._name = f"{self.__class__.__name__}_{uuid4().int}" if name is None else name

        self.inputs = ArbitratingIOManager(
            visible_groups={"required", "optional"},
            name=f"{self._name}_inputs",
            default_io_type=IOContextualQueue,
        )
        self.outputs = ArbitratingIOManager(visible_groups={"required"}, name=f"{self._name}_outputs")

        self.setup_kwargs = self.setup_kwargs.copy()
        self.evaluate_kwargs = self.evaluate_kwargs.copy()
        self.teardown_kwargs = self.teardown_kwargs.copy()

        self._evaluate_tasks = deque()

        self.futures = []

        # Parent Attributes #
        super().__init__(*args, init=False, **kwargs)

        # Construct #
        if init:
            self.construct(
                *args,
                will_proxy=will_proxy,
                will_produce=will_produce,
                init_io=init_io,
                init_setup=init_setup,
                setup_kwargs=setup_kwargs,
                start_server=start_server,
                proxy_context=proxy_context,
                _state=_state,
                **kwargs,
            )

    # Pickling
    def __getstate__(self) -> None | dict[str, Any] | tuple[dict[str, Any] | None, dict[str, Any]]:
        """Gets the object's state for pickling.

        Returns:
            The state returned will be either of the following types based on the presence of __dict__ and __slots__:
                None: __dict__ nor __slots__ are present.
                dict: __dict__ is present and __slots__ is not present.
                tuple[None, dict]: __dict__ is not present and __slots__ is present.
                tuple[dict, dict]: __dict__ is present and __slots__ is present.
        """
        state = super().__getstate__()
        for name in {"async_event_loop", "linked"}:
            if name in state:
                del state[name]
        return state

    def __setstate__(self, state: Any) -> None:
        """Sets the object's state from a pickled state.

        By default, the state can be one of the following types with the corresponding behavior:
            None: Will not set any state.
            dict: Will set the __dict__ attribute to the state.
            tuple[None, dict]: Will set the slot values to the second dict of the tuple.
            tuple[dict, dict]: Will set the __dict__ attribute to the first dict of the tuple and set the slot values
                to the second dict of the tuple.

        Args:
            state: An object which can be used to set the state of this object.
        """
        super().__setstate__(state)
        # self.async_event_loop = get_event_loop()

    # Representation
    def __repr__(self) -> str:
        return f"<{self._name}: {super().__repr__()}>"

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        *args: Any,
        name: str | None = None,
        will_proxy: bool | None = None,
        will_produce: bool | None = None,
        init_io: bool = True,
        init_setup: bool | None = None,
        setup_kwargs: dict[str, Any] | None = None,
        start_server: bool = False,
        proxy_context: BaseProcessingContext | None = None,
        _state: dict[str, Any] | None = None,
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
        if name is not None:
            self.name = name

        if will_proxy is not None:
            self.will_proxy = will_proxy

        if will_produce is not None:
            self.will_produce = will_produce

        if setup_kwargs is not None:
            self.setup_kwargs.update(setup_kwargs)

        if init_io and _state is None:
            self.create_io()
            self.build_io()

        if _state is not None and "_will_proxy" in _state:
            del _state["_will_proxy"]

        if _state is None and (init_setup or (init_setup is None and self.init_setup)):
            self.ensure_setup(**({} if setup_kwargs is None else setup_kwargs))

        # Construct Parent #
        super().construct(*args, start_server=start_server, proxy_context=proxy_context, _state=_state, **kwargs)

    # State
    def is_executing(self) -> bool:
        """Checks if this object is currently running.

        Returns:
            bool: If this object is currently running.
        """
        return self._is_executing

    def _set_executing(self) -> None:
        """Sets the state of this block to executing."""
        self._is_executing = True

    def _clear_executing(self) -> None:
        """Sets the state of this block to not executing."""
        if self._is_executing:
            self._is_executing = False

            for fut in self._executing_waiters:
                if not fut.done():
                    fut.set_result(True)

            self._executing_waiters.clear()

    @contextmanager
    def _executing_context_manager(self) -> None:
        try:
            self._set_executing()
            yield None
        finally:
            self._clear_executing()

    def is_loop_event(self) -> bool:
        """Gets whether this object is currently running an execution loop."""
        return self._loop_event

    def set_loop_event(self) -> None:
        """Sets the execution loop event."""
        self._loop_event = True

    def clear_loop_event(self) -> None:
        """Clears the execution loop event."""
        self._loop_event = False

    # IO Management
    def create_io(
        self,
        input_names: str | Iterable[str] | None = None,
        output_names: str | Iterable[str] | None = None,
        input_signal_names: str | Iterable[str] | None = None,
        output_signal_names: str | Iterable[str] | None = None,
        *args: Any,
        optional_input_names: str | Iterable[str] | None = None,
        **kwargs: Any,
    ) -> None:
        """Creates the IO for this object.

        Args:
            input_names: The names of the inputs to create.
            output_names: The names of the outputs to create.
            input_signal_names: The names of the input signals to create.
            output_signal_names: The names of the output signals to create.
            *args: The arguments for constructing the io.
            optional_input_names: The names of the optional input names.
            **kwargs: The keyword arguments for constructing the io.
        """
        if input_names is None:
            input_names = self.default_input_names
        if output_names is None:
            output_names = self.default_output_names
        if input_signal_names is None:
            input_signal_names = set(self.default_input_signal_names) | set(self._default_input_signal_names)
        if output_signal_names is None:
            output_signal_names = set(self.default_output_signal_names) | set(self._default_output_signal_names)
        if optional_input_names is None:
            optional_input_names = self.default_optional_input.keys()

        # Create Inputs
        optional_input = set(optional_input_names)
        required_input = set(input_names) - optional_input
        input_groups = {"required": required_input, "optional": optional_input, "block": (self.input_link_name,)}
        self.inputs.create_ios(groups=input_groups, *args, **kwargs)
        self.inputs.default_values.update(self.default_optional_input)
        self.inputs.create_groups_to_io_callback(
            groups="required",
            io_name=self.input_link_name,
            put="after_put",
            put_async="after_put_async",
            get_groups=("required", "optional"),
        )
        self.inputs.io_objects[self.input_link_name] = self.create_io_wrapper(
            get=self.io_wrapper_get_method,
            get_async=self.io_wrapper_get_async_method,
            put=self.io_wrapper_put_method,
            put_async=self.io_wrapper_put_async_method,
        )

        # Create Input Signals
        input_signals = self.inputs.create_io(name=self.signal_io_name, group="signals", type_=self.signals_type)
        input_signals.default_io_type = IOQueue
        input_signals.name = f"{self._name}_input_signals"
        input_signals.put.select("put_item")
        input_signals.put_async.select("put_item_async")
        input_signals.create_ios(names=input_signal_names, group="signals")
        self.register_io_signals(input_signals)
        self.inputs.encapsulate_io(input_signals)

        # Create Outputs
        output_groups = {"required": output_names}
        self.outputs.create_ios(groups=output_groups, *args, **kwargs)

        # Create Output Signals
        output_signals = self.outputs.create_io(name=self.signal_io_name, group="signals", type_=self.signals_type)
        output_signals.name = f"{self._name}_output_signals"
        output_signals.put.select("put_all")
        output_signals.put_async.select("put_all_async")
        output_signals.create_ios(names=output_signal_names, group="signals")
        self.outputs.encapsulate_io(output_signals)

    def build_inputs(self, *args: Any, **kwargs: Any) -> None:
        """Builds the inputs with the default settings and routing.

        Args:
            *args: Positional arguments for creating the inputs.
            **kwargs: Keyword arguments for creating the inputs.
        """

    def build_outputs(self, *args: Any, **kwargs: Any) -> None:
        """Builds the outputs with the default settings and routing.

        Args:
            *args: Positional arguments for creating the outputs.
            **kwargs: Keyword arguments for creating the outputs.
        """

    def build_io(self, input_kwargs: dict[str, Any] | None = None, output_kwargs: dict[str, Any] | None = None) -> None:
        """Builds the IO with the default settings and routing.

        Args:
            input_kwargs: Keyword arguments for creating the inputs.
            output_kwargs: Keyword arguments for creating the outputs.
        """
        self.build_inputs(**(input_kwargs or {}))
        self.build_outputs(**(output_kwargs or {}))

    # IO Signals
    def format_signal_callback(
        self,
        name: str,
        signals: str | Iterable[str],
        create_kwargs: dict | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Formats and creates a dictionary representing signal callback configurations.

        This function generates a dictionary that includes the provided name, signals, and other callback configuration
        parameters. It merges the given configurations with additional optional keyword arguments, allowing for a
        flexible customization of the returned dictionary. If `create_kwargs` is provided, it merges this dictionary
        with the base configuration.

        Args:
            name: The name of the input/output signal group.
            signals: A single signal or an iterable collection of signals associated with the callback.
            create_kwargs: An optional dictionary of additional configuration parameters to merge into the output.
            **kwargs: Additional keyword arguments to customize further callback-related configurations.

        Returns:
            dict: A dictionary containing the signal callback configurations.
        """
        return {
            "ios": signals,
            "io_name": name,
            "put": "after_put",
            "put_async": "after_put_async",
        } | (create_kwargs or {})

    def register_io_signals(self, router: IORouter) -> None:
        """Registers I/O signals with the specified IORouter instance.

        Uses the signal_callback_map and registers each signal with the router, by creating the corresponding IO and
        setting up the appropriate callbacks. It facilitates the routing and handling of I/O operations based on
        predefined signal definitions and callback configurations.

        Args:
            router: The IORouter to register I/O signals and callbacks to.
        """
        for name, entry in (self._signal_callback_map_ | self.signal_callback_map).items():
            router.create_io(name=name, group="block")
            router.create_ios_to_io_callback(**self.format_signal_callback(name, **entry))
            method = entry["method"]
            method_async = entry.get("method_async", None)
            io_wrapper = self.create_io_wrapper(put=method, put_async=method_async)
            router.io_objects[name] = io_wrapper

    # IO Linking
    def create_io_wrapper(
        self,
        get: str | None = None,
        get_async: str | None = None,
        put: str | None = None,
        put_async: str | None = None,
    ) -> IOArbitratorWrapper:
        """Creates an IOArbitratorWrapper with wrapping this object.

        Uses the provided `get`, `get_async`, `put`, and `put_async` method names as the methods for the
        IOArbitratorWrapper methods. It checks that the methods exist and assigns the asynchronous variants of the
        methods if not provided.

        Args:
            get: The name of the method for the "get" operation.
            get_async: The name of the asynchronous method for the "get" operation.
            put: The name of the method for the "put" operation.
            put_async: The name of the asynchronous method for the "put" operation.

        Returns:
            IOArbitratorWrapper: An instance of IOArbitratorWrapper configured with the given method names.

        Raises:
            AttributeError: If any method name provided does not exist.
        """
        # Error Check Methods
        if get_async is not None:
            getattr(self, get_async)  # Check if method exists, raise the Attribute Error if not.

        if get is not None:
            getattr(self, get)  # Check if method exists, raise the Attribute Error if not.
            if get_async is None and hasattr(self, f"{get}_async"):
                get_async = f"{get}_async"

        if put_async is not None:
            getattr(self, put_async)  # Check if method exists, raise the Attribute Error if not.

        if put is not None:
            getattr(self, put)  # Check if method exists, raise the Attribute Error if not.
            if put_async is None and hasattr(self, f"{put}_async"):
                put_async = f"{put}_async"

        # Create IO Wrapper
        return IOArbitratorWrapper(
            arbitrator=self,
            getter=get,
            getter_async=get_async,
            putter=put,
            putter_async=put_async,
        )

    def set_input_link(
        self,
        get: str | None = None,
        get_async: str | None = None,
        put: str | None = None,
        put_async: str | None = None,
    ) -> None:
        """Sets the main input link from the inputs object to this block.

        An IO wrapper is created with the `create_io_wrapper` method which servers as the link between the inputs and
        the block.

        Args:
            get: The name of the method in this block which the wrapper will call for the "get" operation.
            get_async: The name of the asynchronous method in this block which the wrapper will call for the "get_async"
                operation.
            put: The name of the method in this block which the wrapper will call for the "put" operation.
            put_async: The name of the asynchronous method in this block which the wrapper will call for the "put_async"
                operation.
        """
        if get is None:
            get = self.io_wrapper_get_method
        if get_async is None:
            get_async = self.io_wrapper_get_async_method
        if put is None:
            put = self.io_wrapper_put_method
        if put_async is None:
            put_async = self.io_wrapper_put_async_method

        self.inputs.set_io(self.input_link_name, self.create_io_wrapper(get, get_async, put, put_async))

    async def set_input_link_async(
        self,
        get: str | None = None,
        get_async: str | None = None,
        put: str | None = None,
        put_async: str | None = None,
    ) -> None:
        """Asynchronously sets the main input link from the inputs object to this block.

        An IO wrapper is created with the `create_io_wrapper` method which servers as the link between the inputs and
        the block.

        Args:
            get: The name of the method in this block which the wrapper will call for the "get" operation.
            get_async: The name of the asynchronous method in this block which the wrapper will call for the "get_async"
                operation.
            put: The name of the method in this block which the wrapper will call for the "put" operation.
            put_async: The name of the asynchronous method in this block which the wrapper will call for the "put_async"
                operation.
        """
        if get is None:
            get = self.io_wrapper_get_method
        if get_async is None:
            get_async = self.io_wrapper_get_async_method
        if put is None:
            put = self.io_wrapper_put_method
        if put_async is None:
            put_async = self.io_wrapper_put_async_method

        await self.inputs.set_io_async(self.input_link_name, self.create_io_wrapper(get, get_async, put, put_async))

    def set_signal_links(self, signal_map: dict[str, Any] | None = None) -> None:
        """Sets up signal links from the inputs to this block.

        Sets the input signal links by iterating over the signal callback maps and building the link with an
        IOArbitratorWrapper. For each entry in the signal callback map, it retrieves the methods to which the signal
        will execute (synchronous or asynchronous), constructs an IO wrapper using the respective methods, and sets it
        the inputs with using methods which work for assignment across processes.

        Args:
            signal_map: A dictionary of the signal callback map with the name of the signal and the names of the method
                to use.
        """
        # When signal map is not provided, assign all signals registered in this block
        if signal_map is None:
            signal_map = self._signal_callback_map_ | self.signal_callback_map

        # Use mapping to assign signals
        for name, entry in signal_map.items():
            method = entry["method"]
            method_async = entry.get("method_async", None)
            io_wrapper = self.create_io_wrapper(put=method, put_async=method_async)
            self.inputs.set_inner_io((self.signal_io_name, name), io_wrapper)

    async def set_signal_links_async(self, signal_map: dict[str, Any] | None = None) -> None:
        """Asynchronously sets up signal links from the inputs to this block.

        Sets the input signal links by iterating over the signal callback maps and building the link with an
        IOArbitratorWrapper. For each entry in the signal callback map, it retrieves the methods to which the signal
        will execute (synchronous or asynchronous), constructs an IO wrapper using the respective methods, and sets it
        the inputs with using methods which work for assignment across processes.

         Args:
            signal_map: A dictionary of the signal callback map with the name of the signal and the names of the method
                to use.
        """
        # When signal map is not provided, assign all signals registered in this block
        if signal_map is None:
            signal_map = self._signal_callback_map_ | self.signal_callback_map

        # Use mapping to assign signals, tasks are created for async efficiency
        tasks = deque()
        for name, entry in (self._signal_callback_map_ | self.signal_callback_map).items():
            method = entry["method"]
            method_async = entry.get("method_async", None)
            io_wrapper = self.create_io_wrapper(put=method, put_async=method_async)
            tasks.append(self.inputs.set_inner_io_async((self.signal_io_name, name), io_wrapper))

        # Await Input Change Tasks
        await gather(*tasks)

    def set_inputs_proxy(self, proxy: ProxyInterface, inner: tuple[bool, ...] = (), update: bool = False) -> None:
        self.inputs.set_proxy(proxy, inner, update)

    async def set_inputs_proxy_async(
        self,
        proxy: ProxyInterface,
        inner: tuple[bool, ...] = (),
        update: bool = False,
    ) -> None:
        await self.inputs.set_proxy_async(proxy, inner, update)

    def set_outputs_proxy(self, proxy: ProxyInterface, inner: tuple[bool, ...] = (), update: bool = False) -> None:
        self.outputs.set_proxy(proxy, inner, update)

    async def set_outputs_proxy_async(
        self,
        proxy: ProxyInterface,
        inner: tuple[bool, ...] = (),
        update: bool = False,
    ) -> None:
        await self.outputs.set_proxy_async(proxy, inner, update)

    # IO Operation
    def start_inputs(self) -> None:
        """Starts the input server."""
        if (self.will_proxy or self.inputs.will_proxy) and not self.inputs.is_alive():
            self.inputs.start_server()

    async def start_inputs_async(self) -> None:
        """Asynchronously starts the input server."""
        if (self.will_proxy or self.inputs.will_proxy) and not self.inputs.is_alive():
            self.inputs.start_server()

    def start_outputs(self) -> None:
        """Starts the output server."""
        if (self.will_proxy or self.outputs.will_proxy) and not self.outputs.is_alive():
            self.outputs.start_server()

    async def start_outputs_async(self) -> None:
        """Asynchronously starts the output server."""
        if (self.will_proxy or self.outputs.will_proxy) and not self.outputs.is_alive():
            self.outputs.start_server()

    def start_io(self) -> None:
        """Starts both the inputs and outputs servers."""
        if (self.will_proxy or self.inputs.will_proxy) and not self.inputs.is_alive():
            self.inputs.start_server()
        if (self.will_proxy or self.outputs.will_proxy) and not self.outputs.is_alive():
            self.outputs.start_server()

    async def start_io_async(self) -> None:
        """Asynchronously starts both the inputs and outputs servers."""
        if (self.will_proxy or self.inputs.will_proxy) and not self.inputs.is_alive():
            self.inputs.start_server()
        if (self.will_proxy or self.outputs.will_proxy) and not self.outputs.is_alive():
            self.outputs.start_server()

    def get_proxies(self) -> dict[str, Any]:
        return {"inputs": self.inputs._proxy, "block": self._proxy, "outputs": self.outputs._proxy}

    async def get_proxies_async(self) -> dict[str, Any]:
        return {"inputs": self.inputs._proxy, "block": self._proxy, "outputs": self.outputs._proxy}

    def set_proxies(self, proxies: dict[str, Any]) -> None:
        if (i_proxy := proxies.get("inputs", None)) is not None:
            self.inputs.set_proxy(i_proxy)
        if (b_proxy := proxies.get("block", None)) is not None:
            self.set_proxy(b_proxy)
        if (o_proxy := proxies.get("outputs", None)) is not None:
            self.outputs.set_proxy(o_proxy)

    async def set_proxies_async(self, proxies: dict[str, Any]) -> None:
        coros = deque()
        if (i_proxy := proxies.get("inputs", None)) is not None:
            coros.append(self.inputs.set_proxy_async(i_proxy))
        if (b_proxy := proxies.get("block", None)) is not None:
            coros.append(self.set_proxy_async(b_proxy))
        if (o_proxy := proxies.get("outputs", None)) is not None:
            coros.append(self.outputs.set_proxy_async(o_proxy))
        if coros:
            await gather(*coros)

    def update_proxies(self) -> dict[str, Any]:
        return {"inputs": self.inputs._proxy, "block": self._proxy, "outputs": self.outputs._proxy}

    async def update_proxies_async(self) -> dict[str, Any]:
        return {"inputs": self.inputs._proxy, "block": self._proxy, "outputs": self.outputs._proxy}

    def update_io_proxies(self) -> None:
        """Updates both the inputs' and outputs' proxies to match the current state."""
        self.inputs.update_server()
        self.outputs.update_server()

    async def update_io_proxies_async(self) -> None:
        """Asynchronously updates both the inputs' and outputs' proxies to match the current state.'"""
        await gather(self.inputs.update_server_async(), self.outputs.update_server_async())

    def finalize_io(self) -> None:
        """Finalizes the inputs and outputs before starting the block."""
        self.inputs.register_listener_links()
        self.inputs.start_listeners()
        self.outputs.register_listener_links()
        self.outputs.start_listeners()

    async def finalize_io_async(self) -> None:
        """Asynchronously finalizes the inputs and outputs before starting the block."""
        await gather(self.inputs.register_listener_links_async(), self.outputs.register_listener_links_async())
        await gather(self.inputs.start_listeners_async(), self.outputs.start_listeners_async())

    # Signals
    def stop_signal(self, stop_flag: bool) -> None:
        if stop_flag:
            self.stop_flag = True
            self.stop_as_task()

    async def stop_signal_async(self, stop_flag: bool) -> None:
        if stop_flag:
            self.stop_flag = True
            self.stop_as_task()

    # Workflow Parts [Setup [Input -> Evaluate -> Output] Teardown]
    # Setup
    def setup(self, *args: Any, **kwargs: Any) -> None:
        """A method for setting up the object."""

    async def setup_async(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously runs the setup."""
        if iscoroutinefunction(self.setup):
            await self.setup(*args, **(self.setup_kwargs | kwargs))
        else:
            self.setup(*args, **(self.setup_kwargs | kwargs))

    def ensure_setup(self, *args: Any, **kwargs: Any) -> None:
        if not self._has_setup:
            self.setup(*args, **kwargs)
            self._has_setup = True

    async def ensure_setup_async(self, *args: Any, **kwargs: Any) -> None:
        if not self._has_setup:
            if (setup_task := self._setup_task) is None:
                self._setup_task = setup_task = create_task(self.setup_async(*args, **kwargs))
                setup_task.add_done_callback(self._finish_setup_task)
            await setup_task

    def _finish_setup_task(self, task: Task) -> None:
        self._has_setup = True
        self._setup_task = None

    async def join_setup_async(self) -> None:
        if (setup_task := self._setup_task) is not None:
            await setup_task

    def reset_setup(self, *args: Any, **kwargs: Any) -> None:
        self._has_setup = False

    # Input
    def format_input(
        self,
        inputs: dict[str, Any],
        *args: Any,
        **kwargs: Any,
    ) -> tuple[dict[str, Any] | None, dict[str, bytes] | None]:
        """Formats the given inputs, separating inputs and their identifiers.

        This method iterates through the provided inputs dictionary, checking each value. If a value is an instance of
        `IdentifiedItem`, it extracts the identifier (ID) and the actual data, placing them into separate dictionaries.
        The IDs are stored with the same keys as in the original inputs, facilitating correlation between IDs and data.
        If a value is not an `IdentifiedItem`, it is added to the formatted inputs without modification.

        Args:
            inputs: A dictionary of inputs to be formatted, where keys are input names and values are the input data.
            *args: Arguments which may be specified in an overriding method.
            **kwargs: Keyword arguments which may be specified in an overriding method.

        Returns:
            A tuple containing two dictionaries:
            - The first dictionary contains the formatted inputs with the same keys as the original inputs. If an input
              was an `IdentifiedItem`, its data is extracted and placed here.
            - The second dictionary contains the IDs extracted from any `IdentifiedItem` inputs, with the same keys as
              the original inputs. If an input was not an `IdentifiedItem`, its key will not appear in this dictionary.
        """
        formatted_inputs = {}
        ids = {}
        for k, v in inputs.items():
            if isinstance(v, IdentifiedItem):
                ids[k] = v[0]
                formatted_inputs[k] = v[1]
            else:
                formatted_inputs[k] = v

        return formatted_inputs, ids

    def get_input(
        self,
        *args: Any,
        format_: bool = True,
        format_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        inputs = self.inputs.get(*args, **kwargs)
        return self.format_input(inputs, **(format_kwargs or {})) if format_ else inputs

    async def get_input_async(
        self,
        *args: Any,
        format_: bool = True,
        format_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        inputs = await self.inputs.get_async(*args, **kwargs)
        return self.format_input(inputs, **(format_kwargs or {})) if format_ else inputs

    # Evaluate
    @abstractmethod
    def evaluate(self, *args, input_ids: dict[str, tuple[bytes, ...]] | None = None, **kwargs: Any) -> Any:
        """An abstract method which is the evaluation of this object.

        Args:
            *args: The arguments for evaluating.
            input_ids: The ids of the inputs.
            **kwargs: The keyword arguments for evaluating.

        Returns:
            The result of the evaluation.
        """

    async def evaluate_async(self, *args, input_ids: dict[str, tuple[bytes, ...]] | None = None, **kwargs: Any) -> Any:
        """The asynchronous evaluation of this object.

        Args:
            *args: The arguments for evaluating.
            input_ids: The ids of the inputs.
            **kwargs: The keyword arguments for evaluating.

        Returns:
            The result of the evaluation.
        """
        if iscoroutinefunction(self.evaluate):
            return await self.evaluate(*args, input_ids=input_ids, **kwargs)
        else:
            return self.evaluate(*args, input_ids=input_ids, **kwargs)

    # Output
    def _format_output(
        self,
        outputs: Any,
        ids: dict[str, tuple[bytes, ...]] | tuple[bytes] = (),
        map_outputs: bool | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        """Formats the outputs along with their identifiers into a dictionary for putting to outputs.

        This method takes the outputs from the `evaluate` method and their corresponding identifiers, then formats them
        into a dictionary where each key corresponds to an output name defined in `self.outputs.order`. If there is only
        one output, it creates a single-entry dictionary with the output name as the key. For multiple outputs, it zips
        the output names with the outputs, creating a dictionary of identified items.

        Args:
            outputs: The outputs to be formatted. Can be a single value or a tuple of values.
            ids: A tuple of bytes representing the identifiers for each output. Defaults to an empty tuple.
            *args: Arguments which may be specified in an overriding method.
            **kwargs: Keyword arguments which may be specified in an overriding method.

        Returns:
            A dictionary where keys are output names and values are `IdentifiedItem` instances containing the output
            data and its identifier. Returns `None` if no outputs are provided.
        """
        keys = self.output_order
        if map_outputs or (map_outputs is None and self.output_as_items):
            output_iter = outputs.items()
        elif len(keys) == 1:
            output_iter = ((keys[0], outputs),)
        else:
            output_iter = zip(keys, outputs)

        if not isinstance(ids, dict):
            ids = {k: ids for k in keys}

        return {k: IdentifiedItem(ids.get(k, ()), v) for k, v in output_iter}

    def format_output(
        self,
        outputs: Any,
        ids: dict[str, tuple[bytes, ...]] | tuple[bytes] = (),
        map_outputs: bool | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        return self._format_output(outputs, ids=ids, map_outputs=map_outputs, *args, **kwargs)

    def put_output(
        self,
        output: Any,
        *args: Any,
        format_: bool = True,
        previous_ids: dict[str, tuple[bytes, ...]] | None = None,
        format_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        if format_:
            f_kwargs = {} if previous_ids is None else {"ids": tuple(set(chain.from_iterable(previous_ids.values())))}
            output = self.format_output(output, **(f_kwargs | (format_kwargs or {})))
        self.outputs.put_items(output, *args, **kwargs)

    async def put_output_async(
        self,
        output: Any,
        *args: Any,
        format_: bool = True,
        previous_ids: dict[str, tuple[bytes, ...]] | None = None,
        format_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        if format_:
            f_kwargs = {} if previous_ids is None else {"ids": tuple(set(chain.from_iterable(previous_ids.values())))}
            output = self.format_output(output, **(f_kwargs | (format_kwargs or {})))
        await self.outputs.put_items_async(output, *args, **kwargs)

    # Teardown
    def teardown(self, *args: Any, **kwargs: Any) -> None:
        """A method for tearing down the object."""

    async def teardown_async(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously runs the teardown."""
        if iscoroutinefunction(self.teardown):
            await self.teardown(*args, **(self.teardown_kwargs | kwargs))
        else:
            self.teardown(*args, **(self.teardown_kwargs | kwargs))

    def ensure_teardown(self, *args: Any, **kwargs: Any) -> None:
        if not self._has_torndown:
            self.teardown(*args, **kwargs)
            self._has_torndown = True

    async def ensure_teardown_async(self, *args: Any, **kwargs: Any) -> None:
        if not self._has_torndown:
            if (teardown_task := self._teardown_task) is None:
                self._teardown_task = teardown_task = create_task(self.teardown_async(*args, **kwargs))
                teardown_task.add_done_callback(self._finish_teardown_task)
            await teardown_task

    def _finish_teardown_task(self, task: Task) -> None:
        self._has_torndown = True
        self._teardown_task = None

    async def join_teardown_async(self) -> None:
        if (teardown_task := self._teardown_task) is not None:
            await teardown_task

    def reset_teardown(self, *args: Any, **kwargs: Any) -> None:
        """Resets the teardown method by removing the stored teardown method and re-setting it."""
        self._has_torndown = False

    # Workflows
    # Consume [Input -> Evaluate]
    def _consume(self, *args: Any, **kwargs: Any) -> None:
        """Consumes by getting the inputs and evaluating.

        Args:
            *args: Arguments which may be specified in an overriding method.
            **kwargs: Keyword arguments which may be specified in an overriding method.
        """
        # Ensure Setup is finished
        self.ensure_setup()

        # Get input from input manager and format it
        inputs, ids = self.get_input()
        # Process inputs through the evaluate method and check if the outputs are not the sentinel value
        self.evaluate(input_ids=ids, **inputs)

        # Stop executing
        if self.stop_flag:
            self.stop_as_task(await_production=False)

    def consume(self, *args: Any, **kwargs: Any) -> None:
        with self._executing_context_manager():
            self._consume(*args, **kwargs)

    async def _consume_async(self, *args: Any, **kwargs: Any) -> None:
        # Ensure Setup is finished
        await self.ensure_setup_async()

        evaluate_method = self.evaluate if iscoroutinefunction(self.evaluate) else self.evaluate_async
        inputs, ids = await create_task(self.get_input_async())
        await evaluate_method(input_ids=ids, **inputs)

        if self.stop_flag:
            self.stop_as_task(await_production=False)

    async def consume_async(self, *args: Any, **kwargs: Any) -> None:
        with self._executing_context_manager():
            await self._consume_async(*args, **kwargs)

    # Consumption Loop
    def _consumption_loop(self, *args: Any, **kwargs: Any) -> None:
        # Ensure Setup is finished
        self.ensure_setup()

        while self._loop_event:
            # Get Inputs
            inputs, ids = self.get_input()
            if any((self.inputs.break_sentinel == inputs[n]) for n in self.inputs.io_groups["required"].keys()):
                self._loop_event = False
                continue

            # Evaluate and Output
            self.evaluate(input_ids=ids, **inputs)

            if self.stop_flag:
                self.stop_as_task(await_production=False)
                self._loop_event = False

    async def _consumption_loop_async(self, *args: Any, **kwargs: Any) -> None:
        """An async loop that consumes evaluate consecutively until an event stops it."""
        # Ensure Setup is finished
        if self._setup_task is not None:
            await self._setup_task

        # Get the correct method
        evaluate_method = self.evaluate if iscoroutinefunction(self.evaluate) else self.evaluate_async

        # Loop the evaluation
        while self._loop_event:
            # Get Inputs
            inputs, ids = await create_task(self.get_input_async())
            if any((self.inputs.break_sentinel == inputs[n]) for n in self.inputs.io_groups["required"].keys()):
                self._loop_event = False
                continue

            # Evaluate and Output
            await evaluate_method(input_ids=ids, **inputs)

            if self.stop_flag:
                self.stop_as_task(await_production=False)
                self._loop_event = False

    # Transact [Input -> Evaluate -> Output]
    def _transact(self, *args: Any, **kwargs: Any) -> None:
        """Transacts by getting the inputs, evaluating, and putting to the outputs.

        Args:
            *args: Arguments which may be specified in an overriding method.
            **kwargs: Keyword arguments which may be specified in an overriding method.
        """
        # Ensure Setup is finished
        self.ensure_setup()

        # Get input from input manager and format it
        inputs, ids = self.get_input()
        # Process inputs through the evaluate method and check if the outputs are not the sentinel value
        if (outputs := self.evaluate(input_ids=ids, **inputs)) is not self.no_output_sentinel:
            # If outputs are valid, format and send them to the output manager
            self.put_output(outputs, previous_ids=ids)

        # Stop executing
        if self.stop_flag:
            self.stop_as_task(await_production=False)

    def transact(self, *args: Any, **kwargs: Any) -> None:
        with self._executing_context_manager():
            self._transact(*args, **kwargs)

    async def _transact_async(self, *args: Any, **kwargs: Any) -> None:
        # Ensure Setup is finished
        await self.ensure_setup_async()

        # Get evaluate method
        evaluate_method = self.evaluate if iscoroutinefunction(self.evaluate) else self.evaluate_async

        # Run Transact [Input -> Evaluate -> Output]
        inputs, ids = await create_task(self.get_input_async())
        if (outputs := await evaluate_method(input_ids=ids, **inputs)) is not self.no_output_sentinel:
            await self.put_output_async(outputs, previous_ids=ids)

        # Create Stop task if flags is set
        if self.stop_flag:
            self.stop_as_task(await_production=False)

    async def transact_async(self, *args: Any, **kwargs: Any) -> None:
        with self._executing_context_manager():
            await self._transact_async(*args, **kwargs)

    # Transaction Loop
    def _transaction_loop(self, *args: Any, **kwargs: Any) -> None:
        # Ensure Setup is finished
        self.ensure_setup()

        while self._loop_event:
            # Get Inputs
            inputs, ids = self.get_input()
            if any((self.inputs.break_sentinel == inputs[n]) for n in self.inputs.io_groups["required"].keys()):
                self._loop_event = False
                continue

            # Evaluate and Output
            if (outputs := self.evaluate(input_ids=ids, **inputs)) is not self.no_output_sentinel:
                self.put_output(outputs, previous_ids=ids)

            # Create Stop task if flags is set
            if self.stop_flag:
                self.stop_as_task(await_production=False)
                self._loop_event = False

    async def _transaction_loop_async(self, *args: Any, **kwargs: Any) -> None:
        """An async loop that executes evaluate consecutively until an event stops it."""
        # Ensure Setup is finished
        await self.ensure_setup_async()

        # Get evaluate method
        evaluate_method = self.evaluate if iscoroutinefunction(self.evaluate) else self.evaluate_async

        # Loop the Transaction [Input -> Evaluate -> Output]
        while self._loop_event:
            # Get Inputs
            inputs, ids = await create_task(self.get_input_async())
            if any((self.inputs.break_sentinel == inputs[n]) for n in self.inputs.io_groups["required"].keys()):
                self._loop_event = False
                continue

            # Evaluate and Output
            if (outputs := await create_task(evaluate_method(input_ids=ids, **inputs))) is not self.no_output_sentinel:
                await create_task(self.put_output_async(outputs, previous_ids=ids))

            # Create Stop task if flags is set
            if self.stop_flag:
                self.stop_as_task(await_production=False)
                self._loop_event = False

    # Produce [Evaluate -> Output]
    def _produce(self, inputs: dict[str, Any] | None = None, *args: Any, **kwargs: Any) -> None:
        """Produces by formatting any given inputs, evaluating, and putting to the outputs.

        Args:
            inputs: Optional inputs to be used in the evaluation.
            *args: Arguments which may be specified in an overriding method.
            **kwargs: Keyword arguments which may be specified in an overriding method.
        """
        # Ensure Setup is finished
        self.ensure_setup()

        # Format any given inputs
        inputs, ids = ({}, None) if inputs is None else self.format_input(inputs)
        # Process inputs through the evaluate method and check if the outputs are not the sentinel value
        if (outputs := self.evaluate(input_ids=ids, **inputs)) is not self.no_output_sentinel:
            # If outputs are valid, format and send them to the output manager
            self.put_output(outputs, previous_ids=ids)

        if self.stop_flag:
            self.stop_as_task(await_production=False)

    def produce(self, *args: Any, **kwargs: Any) -> None:
        with self._executing_context_manager():
            self._produce(*args, **kwargs)

    async def _produce_async(self, inputs: dict[str, Any] | None = None, *args: Any, **kwargs: Any) -> None:
        # Ensure Setup is finished
        await self.ensure_setup_async()

        inputs, ids = ({}, None) if inputs is None else self.format_input(inputs)
        evaluate_method = self.evaluate if iscoroutinefunction(self.evaluate) else self.evaluate_async
        if (outputs := await create_task(evaluate_method(input_ids=ids, **inputs))) is not self.no_output_sentinel:
            await create_task(self.put_output_async(outputs, previous_ids=ids))

        if self.stop_flag:
            self.stop_as_task(await_production=False)

    async def produce_async(self, *args: Any, **kwargs: Any) -> None:
        with self._executing_context_manager():
            await self._produce_async(*args, **kwargs)

    # Production Loop
    def _production_loop(self, *args: Any, **kwargs: Any) -> None:
        # Ensure Setup is finished
        self.ensure_setup()

        while self._loop_event:
            # Evaluate and Output
            if (outputs := self.evaluate(*args, **kwargs)) is not self.no_output_sentinel:
                self.put_output(outputs)

            if self.stop_flag:
                self.stop_as_task(await_production=False)
                self._loop_event = False

    async def _production_loop_async(self, *args: Any, **kwargs: Any) -> None:
        """An async loop that executes evaluate consecutively and outputs until an event stops it."""
        # Ensure Setup is finished
        await self.ensure_setup_async()

        # Get the correct method
        evaluate_method = self.evaluate if iscoroutinefunction(self.evaluate) else self.evaluate_async

        # Loop the evaluation
        while self._loop_event:
            # Evaluate and Output
            if (outputs := await create_task(evaluate_method(*args, **kwargs))) is not self.no_output_sentinel:
                await create_task(self.put_output_async(outputs))

            # Create Stop task if flags is set
            if self.stop_flag:
                self.stop_as_task(await_production=False)
                self._loop_event = False

    # Starting and Running
    # Run Block Once
    async def _run(
        self,
        s_kwargs: dict[str, Any] | None = None,
        e_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Runs a single transaction of the block.

        Args:
            s_kwargs: The keyword arguments for block setup.
            e_kwargs: The keyword arguments for block evaluation.
            t_kwargs: The keyword arguments for block teardown.
        """
        # Flag On
        with self._executing_context_manager():
            # Optionally Setup
            await self.ensure_setup_async(**(s_kwargs or {}))

            # Run one Transaction
            await self._transact_async(**(e_kwargs or {}))

            # Optionally Teardown
            await self.ensure_teardown_async(**(t_kwargs or {}))

            # Wait for any remaining Futures
            for future in self.futures:
                await future

    def _run_async_loop(
        self,
        s_kwargs: dict[str, Any] | None = None,
        e_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Runs a single transaction of the block using the async event loop.

        Args:
            s_kwargs: The keyword arguments for block setup.
            e_kwargs: The keyword arguments for block evaluation.
            t_kwargs: The keyword arguments for block teardown.
        """
        run(self._run(s_kwargs, e_kwargs, t_kwargs))

    def run(
        self,
        as_proxy: bool | None = None,
        s_kwargs: dict[str, Any] | None = None,
        e_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Runs a single transaction of the block, arbitrating to another process if selected.

        Args:
            as_proxy: Determines if this object should run in a separate process.
            s_kwargs: The keyword arguments for block setup.
            e_kwargs: The keyword arguments for block evaluation.
            t_kwargs: The keyword arguments for block teardown.
        """
        # Raise Error if the task is already running.
        if self.is_executing():
            raise RuntimeError(f"{self} task is already running.")

        # Run as Proxy
        if as_proxy or (as_proxy is None and self.will_proxy):
            if not self.is_alive():
                self._start_server()
            self._proxy.run(None, s_kwargs, e_kwargs, t_kwargs)
        elif (loop := self.async_event_loop) is not None:
            run_coroutine_threadsafe(self._run(s_kwargs, e_kwargs, t_kwargs), loop)
        else:
            self._run_async_loop(s_kwargs, e_kwargs, t_kwargs)

    async def run_async(
        self,
        as_proxy: bool | None = None,
        s_kwargs: dict[str, Any] | None = None,
        e_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
    ) -> None:
        """Asynchronously runs a single transaction of the block, arbitrating to another process if selected.

        Args:
            as_proxy: Determines if this object should run in a separate process.
            s_kwargs: The keyword arguments for block setup.
            e_kwargs: The keyword arguments for block evaluation.
            t_kwargs: The keyword arguments for block teardown.
        """
        # Raise Error if the task is already running.
        if self.is_executing():
            raise RuntimeError(f"{self} task is already running.")

        # Use Correct Context
        if as_proxy or (as_proxy is None and self.will_proxy):
            if not self.is_alive():
                self._start_server()
            await self._proxy.run_async(None, s_kwargs, e_kwargs, t_kwargs)
        else:
            await self._run(s_kwargs, e_kwargs, t_kwargs)

    # Start Proxy
    def start_proxy(self, as_proxy: bool | None = None, update_local: bool = False, update_io: bool = False) -> None:
        """Starts the proxy server for this block.

        Args:
            update_local: Determines if the local objects' proxies will be updated from the other proxies.
            update_io: Determines if the IO should be updated.
        """
        if as_proxy or (as_proxy is None and self.will_proxy) and not self.is_alive():
            # Start proxy servers
            self.start_outputs()
            self._start_server()
            self.start_inputs()
            # Set the inputs proxy on this object's proxy
            self.set_inputs_proxy(self.inputs._proxy)

        # Update Proxy References
        if update_local:
            # Cascade update all the proxies so they have the references/links to the other proxies.
            self.update_proxies()

        # Update IO
        if update_io:
            # Cascade update all the IO objects so they have the references/link to the other proxies.
            self.update_io_proxies()

    async def start_proxy_async(
        self,
        as_proxy: bool | None = None,
        update_local: bool = False,
        update_io: bool = False,
    ) -> None:
        """Asynchronously starts the proxy server for this block.

        Args:
            update_local: Determines if the local objects' proxies will be updated from the other proxies.
            update_io: Determines if the IO should be updated.
        """
        if as_proxy or (as_proxy is None and self.will_proxy) and not self.is_alive():
            # Start proxy servers
            self.start_outputs()
            self._start_server()
            self.start_inputs()
            # Set the inputs proxy on this object's proxy
            await self.set_inputs_proxy_async(self.inputs._proxy)

        # Update Proxy References
        if update_local:
            # Cascade update all the proxies so they have the references/links to the other proxies.
            await self.update_proxies_async()

        # Update IO
        if update_io:
            # Cascade update all the IO objects so they have the references/link to the other proxies.
            await self.update_io_proxies_async()

    # Start Block
    async def _start_async(self, s_kwargs: dict[str, Any] | None = None) -> None:
        """Starts the continuous execution of the block.

        Args:
            s_kwargs: The keyword arguments for block setup.
        """
        self._set_executing()

        # Optionally Setup
        await self.ensure_setup_async(**(s_kwargs or {}))

        if self.will_produce:
            self.set_loop_event()
            self._production_task = create_task(self._production_loop_async())

    def _start_async_loop(self, s_kwargs: dict[str, Any] | None = None) -> None:
        """Starts the continuous execution of the block in an async run.

        Args:
            s_kwargs: The keyword arguments for block setup.
        """
        run(self._start_async(s_kwargs))

    def start(
        self,
        as_proxy: bool | None = None,
        s_kwargs: dict[str, Any] | None = None,
        finalize: bool = True,
    ) -> None:
        """Starts the continuous execution of the block, arbitrating to another process if selected.

        Args:
            as_proxy: Determines if this object should run in a separate process.
            s_kwargs: The keyword arguments for block setup.
            finalize: Determines if the block will finalize the IO.
        """
        # Raise Error if the task is already running.
        if self.is_executing():
            raise RuntimeError(f"{self} task is already running.")

        # Start Proxy Servers (Determined in the method)
        self.start_proxy(as_proxy)

        # Finalize IO
        if finalize:
            self.finalize_io()

        # Start and Use Correct Context
        if self.is_alive():
            self._proxy.start(None, s_kwargs, finalize=False)
        elif (loop := self.async_event_loop) is not None:
            run_coroutine_threadsafe(self._start_async(s_kwargs), loop)
        else:
            self._start_async_loop(s_kwargs)

    async def start_async(
        self,
        as_proxy: bool | None = None,
        s_kwargs: dict[str, Any] | None = None,
        finalize: bool = True,
    ) -> None:
        """Asynchronously starts the continuous execution of the block, arbitrating to another process if selected.

        Args:
            as_proxy: Determines if this object should run in a separate process.
            s_kwargs: The keyword arguments for block setup.
            finalize: Determines if the block will finalize the IO.
        """
        # Raise Error if the task is already running.
        if self.is_executing():
            raise RuntimeError(f"{self} task is already running.")

        # Start Proxy Servers (Determined in the method)
        await self.start_proxy_async(as_proxy)

        # Finalize IO
        if finalize:
            await self.finalize_io_async()

        # Start Use Correct Context
        if self.is_alive():
            await self._proxy.start_async(None, s_kwargs, finalize=False)
        else:
            await self._start_async(s_kwargs)

    # Stop Block
    async def _stop_block_async(
        self,
        join_io: bool = True,
        await_production: bool = True,
        join_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        # Join IO
        if join_io:
            await self.inputs.join_all_async(**(join_kwargs or {}))

        # Stop Production Task
        if self._production_task is not None:
            self.clear_loop_event()
            if await_production:
                await self._production_task
                self._production_task = None

        # Optionally Teardown
        await self.ensure_teardown_async(**(t_kwargs or {}))

        # Wait for any remaining Futures
        for future in self.futures:
            await future

        self._clear_executing()

    async def stop_block_async(
        self,
        join_io: bool = True,
        await_production: bool = True,
        join_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        await self._stop_block_async(
            join_io=join_io,
            await_production=await_production,
            join_kwargs=join_kwargs,
            t_kwargs=t_kwargs,
            **kwargs,
        )
        await gather(*(self.inputs.stop_async(), self.outputs.stop_async()))
        await gather(*(self.inputs.stop_server_async(update=False), self.outputs.stop_server_async(update=False)))

    def stop(
        self,
        t_kwargs: dict[str, Any] | None = None,
        server: bool = True,
        update: bool = True,
        join_io: bool = True,
        join_kwargs: dict[str, Any] | None = None,
        await_production: bool = True,
        **kwargs: Any,
    ) -> None:
        """Stops the execution of this block, optionally stopping the server relative to this object.

        Args:
            server: Determines if the remote server should be stopped.
            update: Determines if this object should be updated from the server before stopping.
        """
        if self.is_alive() and server:
            self._proxy.stop_block_async(
                join_io=join_io,
                await_production=await_production,
                join_kwargs=join_kwargs,
                t_kwargs=t_kwargs,
                **kwargs,
            )
            if update:
                self.join_execution()
            self._stop_server(update)
        elif (loop := self.async_event_loop) is not None:
            coro = self._stop_block_async(
                join_io=join_io,
                await_production=await_production,
                join_kwargs=join_kwargs,
                t_kwargs=t_kwargs,
                **kwargs,
            )
            run_coroutine_threadsafe(coro, loop)
            self.inputs.stop()
            self.outputs.stop()
        else:
            run(self._stop_block_async(
                join_io=join_io,
                await_production=await_production,
                join_kwargs=join_kwargs,
                t_kwargs=t_kwargs,
                **kwargs,
            ))
            self.inputs.stop()
            self.outputs.stop()

    async def stop_async(
        self,
        t_kwargs: dict[str, Any] | None = None,
        server: bool = True,
        update: bool = True,
        join_io: bool = True,
        join_kwargs: dict[str, Any] | None = None,
        await_production: bool = True,
        **kwargs: Any,
    ) -> None:
        """Asynchronously Stops the execution of this block, optionally stopping the server relative to this object.

        Args:
            server: Determines if the remote server should be stopped.
            update: Determines if this object should be updated from the server before stopping.
        """
        if self.is_alive() and server:
            await self._proxy.stop_block_async(
                join_io=join_io,
                await_production=await_production,
                join_kwargs=join_kwargs,
                t_kwargs=t_kwargs,
                **kwargs,
            )
            if update:
                await self.join_execution_async()
            await self._stop_server_async(update)
        else:
            await self._stop_block_async(
                join_io=join_io,
                await_production=await_production,
                join_kwargs=join_kwargs,
                t_kwargs=t_kwargs,
                **kwargs,
            )
            await gather(*(self.inputs.stop_async(), self.outputs.stop_async()))

    def stop_as_task(self, *args, **kwargs) -> None:
        if self.stop_task is None:
            self.stop_task = task = create_task(self.stop_async(*args, **kwargs))
            task.add_done_callback(self._remove_stop_task)

    def _remove_stop_task(self, task: Task) -> None:
        self.stop_task = None

    # Join Execution
    async def join_stop_task_async(self, timeout: float | None = None) -> None:
        if self.stop_task is not None:
            await wait_for(self.stop_task, timeout)

    def join_execution(self, timeout: float | None = None) -> None:
        """Waits until the execution of the block has finished.

        Args:
            timeout: The time, in seconds, to wait for the block to finish.
        """
        if timeout is None:
            while self.is_executing():
                pass
        else:
            deadline = perf_counter() + timeout
            while self.is_executing():
                if deadline <= perf_counter():
                    return

    async def join_execution_async(self, timeout: float | None = None) -> None:
        """Asynchronously waits until the execution of the block has finished.

        Args:
            timeout: The time, in seconds, to wait for the block to finish.
            interval: The time, in seconds, between each join check.
        """
        if self._is_executing:
            fut = self.async_event_loop.create_future()
            self._executing_waiters.append(fut)

            try:
                await wait_for(fut, timeout)
            except:
                fut.cancel()  # Just in case future is not done yet.
                try:
                    # Clean self._executing_waiters from canceled future.
                    self._executing_waiters.remove(fut)
                except ValueError:
                    # The future could be removed from self._executing_witers by a
                    # previous put_nowait call.
                    pass

    async def join_async(self, timeout: float | None = None) -> None:
        await self.join_execution_async(timeout)
        await self.join_stop_task_async(timeout)
