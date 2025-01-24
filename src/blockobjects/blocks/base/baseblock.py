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
from baseobjects.functions import CallableMultiplexObject, MethodMultiplexer
from ...process import ProcessArbitrator, arbitratemethod
from ...process.context import BaseProcessingContext, ContextualEvent

# Local Packages #
from ...io import IORouter, ArbitratingIOManager, IdentifiedItem


# Definitions #
# Classes #
class BaseBlock(ProcessArbitrator, CallableMultiplexObject):
    """An abstract class which defines a Block, an easily definable data processing block with inputs and outputs.

    In subclasses the "evaluate" method must be defined as it is data processing element of this object. Additionally,
    the "input_names" and "output_names" must be defined to ensure the IO is mapped properly. "input_names" must match
    the keyword arguments of the "evaluate" method. "output_names" are names for each of the elements of the outputs
    tuple of the "evaluate" method.

    "evaluate" can be called directly which will run without using the Block IO. This is useful for processing data
    without using the Object IO architecture.

    To use the Object IO architecture "execute" should be called. "execute" first gets the inputs from the inputs
    manager and passes it to "evaluate" method. After evaluating, the output from "evaluate" is then put into the
    outputs manager to be used later.

    "execute" is also MethodMultiplexer, meaning that its call is arbitrated to different specified method. This gives
    Block the flexibility to change the "execute" method's implementation during runtime.

    Class Attributes:
        default_execute: The default name of the method to use for execution.
        default_input_names: The default ordered tuple with the names of the inputs to an Block.
        default_output_names: The default ordered tuple with the names of the outputs to an Block.

    Attributes:
        inputs: The inputs manager of the Block.
        outputs: The outputs manager of the Block.
        execute: The method multiplexer which manages which execute method to run when called.
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
    # Static Methods #
    @staticmethod
    def call_method(obj, *args, method_name: str, **kwargs) -> None:
        return getattr(obj, method_name)(*args, **kwargs)

    @staticmethod
    async def call_method_async(obj, *args, method_name: str, **kwargs) -> None:
        return getattr(obj, method_name)(*args, **kwargs)

    @staticmethod
    async def call_async_method_async(obj, *args, method_name: str, **kwargs) -> None:
        return await getattr(obj, method_name)(*args, **kwargs)

    # Class Attributes #
    public_exposed: ClassVar[bool] = False
    exposed: ClassVar[set] = {
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
    default_input_signal_names: ClassVar[tuple[str, ...]] = ()
    default_optional_input: ClassVar[dict[str, Any]] = {}
    default_output_names: ClassVar[tuple[str, ...]] = ()
    default_output_signal_names: ClassVar[tuple[str, ...]] = ()

    init_setup: ClassVar[bool] = True

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

    # IO
    sets_up_io: bool = True
    actualize_io_: bool = True
    inputs: ArbitratingIOManager
    outputs: ArbitratingIOManager

    signal_io_name: str = "block_signals"
    signals_type: type[IORouter] = IORouter
    signal_callback_map: dict[str, tuple[str, str, dict[str, Any]]] = {}

    _output_order: tuple[str, ...] | None = None
    output_as_items: bool = False
    no_output_sentinel: Any = SentinelObject("no_output_sentinel")

    input_callback_method: str = "_produce"
    input_callback_method_async: str = "_produce_async"

    get_input_method: str = "_get_input"
    get_input_method_async: str = "_get_input_async"
    get_input: MethodMultiplexer
    get_input_async: MethodMultiplexer
    put_output_method: str = "_put_output"
    put_output_method_async: str = "_put_output_async"
    put_output: MethodMultiplexer
    put_output_async: MethodMultiplexer

    # Setup/Evaluate/Teardown
    sets_up: bool = True
    tears_down: bool = True

    setup_kwargs: dict[str, Any] = {}
    evaluate_kwargs: dict[str, Any] = {}
    teardown_kwargs: dict[str, Any] = {}

    _setup: MethodMultiplexer
    _evaluate: MethodMultiplexer
    _teardown: MethodMultiplexer

    _production_task: Task | None = None

    stop_flag: bool = False

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
        self.signal_callback_map = self.signal_callback_map.copy()

        self._name = f"{self.__class__.__name__}_{uuid4().int}" if name is None else name

        self.inputs = ArbitratingIOManager(visible_groups={"required", "optional"}, name=f"{self._name}_inputs")
        self.outputs = ArbitratingIOManager(visible_groups={"required"}, name=f"{self._name}_outputs")

        self.setup_kwargs = self.setup_kwargs.copy()
        self.evaluate_kwargs = self.evaluate_kwargs.copy()
        self.teardown_kwargs = self.teardown_kwargs.copy()

        self.get_input = MethodMultiplexer(instance=self)
        self.get_input_async = MethodMultiplexer(instance=self)
        self.put_output = MethodMultiplexer(instance=self)
        self.put_output_async = MethodMultiplexer(instance=self)

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
    def __getstate__(self) -> dict[str, Any]:
        """Creates a dictionary of attributes which can be used to rebuild this object.

        Returns:
            A dictionary of this object's attributes.
        """
        state = super().__getstate__()
        for name in {"async_event_loop", "linked"}:
            if name in state:
                del state[name]
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Builds this object based on a dictionary of corresponding attributes.

        Args:
            state: The attributes to build this object from.
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

        if _state is not None and "_will_proxy" in _state:
            del _state["_will_proxy"]

        if _state is None and (init_setup or (init_setup is None and self.init_setup)):
            self.setup(**({} if setup_kwargs is None else setup_kwargs))

        # Construct Parent #
        super().construct(*args, start_server=start_server, proxy_context=proxy_context, _state=_state, **kwargs)

        if _state is not None:
            self.set_execution_io()

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

    # IO
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
            **kwargs: The keyword arguments for constructing the io.
        """
        if input_names is None:
            input_names = self.default_input_names
        if output_names is None:
            output_names = self.default_output_names
        if input_signal_names is None:
            input_signal_names = self.default_input_signal_names
        if output_signal_names is None:
            output_signal_names = self.default_output_signal_names
        if optional_input_names is None:
            optional_input_names = self.default_optional_input.keys()

        # Create Inputs
        optional_input = set(optional_input_names)
        required_input = set(input_names) - optional_input
        input_groups = {"required": required_input, "optional": optional_input}
        self.inputs.create_ios(groups=input_groups, *args, **kwargs)
        self.inputs.default_values.update(self.default_optional_input)

        # Create Input Signals
        input_signals = self.inputs.create_io(name=self.signal_io_name, group="signals", type_=self.signals_type)
        input_signals.name = f"{self._name}_input_signals"
        input_signals.put.select("put_item_callback")
        input_signals.put_async.select("put_item_callback_async")
        input_signals.create_ios(names=input_signal_names, group="signals")
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

        # Setup IO Connections
        self.setup_io()

    def build_io(self, *args: Any, override: bool = False, **kwargs: Any) -> None:
        """Builds the IO with the default routing.

        Args:
            *args: The arguments for creating the io.
            override: Determines if the io will be overridden.
            **kwargs: The keyword arguments for creating the inner blockgroup.
        """

    async def build_io_async(self, *args: Any, override: bool = False, **kwargs: Any) -> None:
        return self.build_io(*args, override=override, **kwargs)

    def setup_io(self, *args: Any, **kwargs: Any) -> None:
        if self.sets_up_io:
            self.build_io(*args, **kwargs)
            self.set_execution_io()
            self.sets_up_io = False

    async def setup_io_async(self, *args: Any, **kwargs: Any) -> None:
        if self.sets_up_io:
            await self.build_io_async(*args, **kwargs)
            self.set_execution_io()
            self.sets_up_io = False

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

    def _format_output(
        self,
        outputs: Any,
        ids: tuple[bytes, ...] = (),
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
        if len(keys) == 1:
            if self.output_as_items and isinstance(outputs, dict):
                return {k: IdentifiedItem(ids, v) for k, v in outputs.items()}
            else:
                return {keys[0]: IdentifiedItem(ids, outputs)}
        else:
            return {k: IdentifiedItem(ids, v) for k, v in zip(keys, outputs)}

    def format_output(
        self,
        outputs: Any,
        ids: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        new_ids = () if ids is None else tuple(set(chain.from_iterable(ids.values())))

        return self._format_output(outputs, ids=new_ids, *args, **kwargs)

    def start_inputs(self) -> None:
        if (self.will_proxy or self.inputs.will_proxy) and not self.inputs.is_alive():
            self.inputs.start_server()

    async def start_inputs_async(self) -> None:
        if (self.will_proxy or self.inputs.will_proxy) and not self.inputs.is_alive():
            self.inputs.start_server()

    def start_outputs(self) -> None:
        if (self.will_proxy or self.outputs.will_proxy) and not self.outputs.is_alive():
            self.outputs.start_server()

    async def start_outputs_async(self) -> None:
        if (self.will_proxy or self.outputs.will_proxy) and not self.outputs.is_alive():
            self.outputs.start_server()

    def start_io(self) -> None:
        if (self.will_proxy or self.inputs.will_proxy) and not self.inputs.is_alive():
            self.inputs.start_server()
        if (self.will_proxy or self.outputs.will_proxy) and not self.outputs.is_alive():
            self.outputs.start_server()

    async def start_io_async(self) -> None:
        if (self.will_proxy or self.inputs.will_proxy) and not self.inputs.is_alive():
            self.inputs.start_server()
        if (self.will_proxy or self.outputs.will_proxy) and not self.outputs.is_alive():
            self.outputs.start_server()

    def materialize_io(self) -> None:
        if self.inputs.is_proxy():
            self.inputs.update_server_io()
            self.inputs.start_listeners()
        if self.outputs.is_proxy():
            self.outputs.update_server_io()
            self.outputs.start_listeners()

    async def materialize_io_async(self) -> None:
        if self.inputs.is_proxy():
            await self.inputs.update_server_io_async()
            await self.inputs.start_listeners_async()
        if self.outputs.is_proxy():
            await self.outputs.update_server_io_async()
            await self.outputs.start_listeners_async()

    def actualize_io(self) -> None:
        if self.sets_up_io:
            if self.inputs.is_proxy():
                self.inputs.update_server_io()
            if self.outputs.is_proxy():
                self.outputs.update_server_io()
            self.sets_up_io = False

    async def actualize_io_async(self) -> None:
        if self.sets_up_io:
            if self.inputs.is_proxy():
                await self.inputs.update_server_io_async()
            if self.outputs.is_proxy():
                await self.outputs.update_server_io_async()
            self.sets_up_io = False

    def _create_callback_info(
        self,
        method: str,
        method_async: str | None = None,
        get_method: str = "get_groups",
        get_method_async: str | None = None,
        condition_method: str = "poll_groups",
        condition_method_async: str | None = None,
        get_kwargs: dict[str, Any] | None = None,
        callback_kwargs: dict[str, Any] | None = None,
        condition_kwargs: dict[str, Any] | None = None,
        manager_kwargs: dict[str, Any] | None = None,
        as_proxy: bool = True,
    ) -> tuple[tuple[dict[str, Any], dict[str, Any], dict[str, Any]], ...]:
        # Create Generic Methods for callback
        callback = partial(self.call_method, method_name=method)

        if method_async is None:
            callback_async = partial(self.call_method_async, method_name=method)
        else:
            callback_async = partial(self.call_async_method_async, method_name=method_async)

        # Use BaseMethod because it uses weak references
        instance = self._proxy if as_proxy and self.is_alive() else self
        method_object = BaseMethod(func=callback, instance=instance)
        method_async_object = BaseMethod(func=callback_async, instance=instance)

        # Set defaults
        if get_kwargs is None:
            get_kwargs = {}
        if callback_kwargs is None:
            callback_kwargs = {}
        if condition_kwargs is None:
            condition_kwargs = {}
        if manager_kwargs is None:
            manager_kwargs = {}

        # Create formatted tuples to pass to callback registration
        callback_info = (
            {"callback": method_object, "get_method": get_method, "get_kwargs": get_kwargs} | callback_kwargs,
            {"method": condition_method} | condition_kwargs,
            {"evaluator": "evaluate_callbacks"},
        )
        callback_async_info = (
            {
                "callback": method_async_object,
                "get_method": get_method_async or f"{get_method}_async",
                "get_kwargs": get_kwargs,
                "as_task": True,
            } | callback_kwargs,
            {"method": condition_method_async or f"{condition_method}_async"} | condition_kwargs,
            {"evaluator": "evaluate_task_callbacks_async"} | manager_kwargs,
        )

        return callback_info, callback_async_info

    def set_input_callback(
        self,
        name: str | None = None,
        name_async: str | None = None,
        as_proxy: bool = True,
    ) -> None:
        # Select Methods from given names
        if name is None:
            name = self.input_callback_method

        if name_async is None:
            name_async = self.input_callback_method_async

        # Create Callback info
        callback_info, callback_async_info = self._create_callback_info(
            method=name,
            method_async=name_async,
            get_method="get_groups",
            get_method_async="get_groups_async",
            get_kwargs={"groups": ("required", "optional")},
            callback_kwargs={"as_first": True},
            condition_kwargs={"groups": ("required",)},
            as_proxy=as_proxy,
        )

        self.inputs.register_callback(("input",) + callback_info, ("input",) +callback_async_info)

    async def set_input_callback_async(
        self,
        name: str | None = None,
        name_async: str | None = None,
        as_proxy: bool = False,
    ) -> None:
        # Select Methods from given names
        if name is None:
            name = self.input_callback_method

        if name_async is None:
            name_async = self.input_callback_method_async

        # Create Callback info
        callback_info, callback_async_info = self._create_callback_info(
            method=name,
            method_async=name_async,
            get_method="get_groups",
            get_method_async="get_groups_async",
            get_kwargs={"groups": ("required", "optional")},
            callback_kwargs={"as_first": True},
            condition_kwargs={"groups": ("required",)},
            as_proxy=as_proxy,
        )

        await self.inputs.register_callback_async(("input",) + callback_info, ("input",) + callback_async_info)

    def format_signal_callback_entry(self, entry: tuple) -> dict[str, Any]:
        return {
            "method": entry[0],
            "get_method": "get_items",
            "condition_method": "poll_all_ios",
            "get_kwargs": {"names": entry[1]},
            "condition_kwargs": {"names": entry[1]},
            "as_proxy": True,
        } | entry[2]

    def set_signal_callbacks(self) -> None:
        callbacks = {}
        callbacks_async = {}
        for name, entry in self.signal_callback_map.items():
            new_kwargs = self.format_signal_callback_entry(entry)
            callbacks[name], callbacks_async[name] = self._create_callback_info(**new_kwargs)

        self.inputs.register_inner_callbacks(self.signal_io_name, callbacks, callbacks_async)

    async def set_signal_callbacks_async(self) -> None:
        callbacks = {}
        callbacks_async = {}
        for name, entry in self.signal_callback_map.items():
            new_kwargs = self.format_signal_callback_entry(entry)
            callbacks[name], callbacks_async[name] = self._create_callback_info(**new_kwargs)

        await self.inputs.register_inner_callbacks_async(self.signal_io_name, callbacks, callbacks_async)

    def finalize_io(self) -> None:
        self.set_input_callback()
        self.set_signal_callbacks()
        self.inputs.start_listeners()
        self.outputs.start_listeners()

    async def finalize_io_async(self) -> None:
        await self.set_input_callback_async()
        await self.set_signal_callbacks_async()
        await self.inputs.start_listeners_async()
        await self.outputs.start_listeners_async()

    # Setup
    def setup(self, *args: Any, **kwargs: Any) -> None:
        """A method for setting up the object."""

    async def setup_async(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously runs the setup."""
        if iscoroutinefunction(self.setup):
            await self.setup(*args, **(self.setup_kwargs | kwargs))
        else:
            self.setup(*args, **(self.setup_kwargs | kwargs))

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
            return await self.evaluate(*args, **kwargs)
        else:
            return self.evaluate(*args, **kwargs)

    # Set Execution
    def set_execution_io(self) -> None:
        match len(self.inputs.io_groups["required"]):
            case 0:
                self.get_input.select("_get_no_input")
                self.get_input_async.select("_get_no_input_async")
            case _:
                self.get_input.select(self.get_input_method)
                self.get_input_async.select(self.get_input_method_async)

        match len(self.outputs.io_groups["required"]):
            case 0:
                self.put_output.select("_put_no_output")
                self.put_output_async.select("_put_no_output_async")
            case _:
                self.put_output.select(self.put_output_method)
                self.put_output_async.select(self.put_output_method_async)

    def set_execution_input_only(self) -> None:
        match len(self.inputs):
            case 0:
                self.get_input.select("_get_no_input")
                self.get_input_async.select("_get_no_input_async")
            case _:
                self.get_input.select(self.get_input_method)
                self.get_input_async.select(self.get_input_method_async)

        self.put_output.select("_put_no_output")
        self.put_output_async.select("_put_no_output_async")

    def set_execution_output_only(self) -> None:
        self.get_input.select("_get_no_input")
        self.get_input_async.select("_get_no_input_async")

        match len(self.outputs.order):
            case 0:
                self.put_output.select("_put_no_output")
                self.put_output_async.select("_put_no_output_async")
            case _:
                self.put_output.select(self.put_output_method)
                self.put_output_async.select(self.put_output_method_async)

    def set_execution_no_io(self) -> None:
        self.get_input.select("_get_no_input")
        self.get_input_async.select("_get_no_input_async")

        self.put_output.select("_put_no_output")
        self.put_output_async.select("_put_no_output_async")

    # Get Input
    def _get_no_input(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {}

    async def _get_no_input_async(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {}

    def _get_input(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.inputs.get(*args, **kwargs)

    async def _get_input_async(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return await self.inputs.get_async(*args, **kwargs)

    # Put Output
    def _put_no_output(self, *args: Any, **kwargs: Any) -> None:
        """Executes no output."""

    async def _put_no_output_async(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously executes no output."""

    def _put_output(self, output: dict[str, Any], **kwargs: Any) -> None:
        self.outputs.put_items_callback(output, **kwargs)

    async def _put_output_async(self, output: dict[str, Any], **kwargs: Any) -> None:
        await self.outputs.put_items_callback_async(output, **kwargs)

    # Execute
    def _execute(self, *args: Any, **kwargs: Any) -> None:
        """Executes by getting the inputs, evaluating, and putting to the outputs.

        Args:
            *args: Arguments which may be specified in an overriding method.
            **kwargs: Keyword arguments which may be specified in an overriding method.
        """
        # Get input from input manager and format it
        inputs, ids = self.format_input(self.get_input())
        # Process inputs through the evaluate method and check if the outputs are not the sentinel value
        if (outputs := self.evaluate(input_ids=ids, **inputs)) is not self.no_output_sentinel:
            # If outputs are valid, format and send them to the output manager
            self.put_output(self.format_output(outputs, ids))

        # Stop executing
        if self.stop_flag:
            self.stop(await_production=False)

    def execute(self, *args: Any, **kwargs: Any) -> None:
        with self._executing_context_manager():
            self._execute(*args, **kwargs)

    async def _execute_async(self, *args: Any, **kwargs: Any) -> None:
        evaluate_method = self.evaluate if iscoroutinefunction(self.evaluate) else self.evaluate_async
        inputs, ids = self.format_input(await self.get_input_async())
        if (outputs := await evaluate_method(input_ids=ids, **inputs)) is not self.no_output_sentinel:
            await self.put_output_async(self.format_output(outputs, ids))

        if self.stop_flag:
            await self.stop_async(await_production=False)

    async def execute_async(self, *args: Any, **kwargs: Any) -> None:
        with self._executing_context_manager():
            await self._execute_async(*args, **kwargs)

    # Execute Loop
    def _execution_loop(self, *args: Any, **kwargs: Any) -> None:
        while self._loop_event:
            # Get Inputs
            inputs, ids = self.format_input(self.get_input())
            if any((self.inputs.break_sentinel == inputs[n]) for n in self.inputs.io_groups["required"].keys()):
                self._loop_event = False
                continue

            # Evaluate and Output
            if (outputs := self.evaluate(input_ids=ids, **inputs)) is not self.no_output_sentinel:
                self.put_output(self.format_output(outputs, ids))

    async def _execution_loop_async(self, *args: Any, **kwargs: Any) -> None:
        """An async loop that executes evaluate consecutively until an event stops it."""
        # Get the correct method
        evaluate_method = self.evaluate if iscoroutinefunction(self.evaluate) else self.evaluate_async

        # Loop the evaluation
        while self._loop_event:
            # Get Inputs
            inputs, ids = self.format_input(await create_task(self.get_input_async()))
            if any((self.inputs.break_sentinel == inputs[n]) for n in self.inputs.io_groups["required"].keys()):
                self._loop_event = False
                continue

            # Evaluate and Output
            if (outputs := await create_task(evaluate_method(input_ids=ids, **inputs))) is not self.no_output_sentinel:
                await create_task(self.put_output_async(self.format_output(outputs, ids)))

    # Produce
    def _produce(self, inputs: dict[str, Any] | None = None, *args: Any, **kwargs: Any) -> None:
        """Produces by formatting any given inputs, evaluating, and putting to the outputs.

        Args:
            inputs: Optional inputs to be used in the evaluation.
            *args: Arguments which may be specified in an overriding method.
            **kwargs: Keyword arguments which may be specified in an overriding method.
        """
        # Format any given inputs
        inputs, ids = ({}, None) if inputs is None else self.format_input(inputs)
        # Process inputs through the evaluate method and check if the outputs are not the sentinel value
        if (outputs := self.evaluate(input_ids=ids, **inputs)) is not self.no_output_sentinel:
            # If outputs are valid, format and send them to the output manager
            self.put_output(self.format_output(outputs, ids))

        if self.stop_flag:
            self.stop(await_production=False)

    def produce(self, *args: Any, **kwargs: Any) -> None:
        with self._executing_context_manager():
            self._produce(*args, **kwargs)

    async def _produce_async(self, inputs: dict[str, Any] | None = None, *args: Any, **kwargs: Any) -> None:
        inputs, ids = ({}, None) if inputs is None else self.format_input(inputs)
        evaluate_method = self.evaluate if iscoroutinefunction(self.evaluate) else self.evaluate_async
        if (outputs := await create_task(evaluate_method(input_ids=ids, **inputs))) is not self.no_output_sentinel:
            await create_task(self.put_output_async(self.format_output(outputs, ids)))

        if self.stop_flag:
            await self.stop_async(await_production=False)

    async def produce_async(self, *args: Any, **kwargs: Any) -> None:
        with self._executing_context_manager():
            await self._produce_async(*args, **kwargs)

    # Production Loop
    def _production_loop(self, *args: Any, **kwargs: Any) -> None:
        while self._loop_event:
            # Evaluate and Output
            if (outputs := self.evaluate(*args, **kwargs)) is not self.no_output_sentinel:
                self.put_output(self.format_output(outputs))

            if self.stop_flag:
                self.stop(await_production=False)

    async def _production_loop_async(self, *args: Any, **kwargs: Any) -> None:
        """An async loop that executes evaluate consecutively and outputs until an event stops it."""
        # Get the correct method
        evaluate_method = self.evaluate if iscoroutinefunction(self.evaluate) else self.evaluate_async

        # Loop the evaluation
        while self._loop_event:
            # Evaluate and Output
            if (outputs := await create_task(evaluate_method(*args, **kwargs))) is not self.no_output_sentinel:
                await create_task(self.put_output_async(self.format_output(outputs)))

            if self.stop_flag:
                await self.stop_async(await_production=False)

    # Teardown
    def teardown(self, *args: Any, **kwargs: Any) -> None:
        """A method for tearing down the object."""

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
    ) -> None:
        """Runs a single execution of the block, arbitrating to another process if selected.

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
        """Asynchronously runs a single execution of the block, arbitrating to another process if selected.

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
            await self._proxy.run_async(None, s_kwargs, e_kwargs, t_kwargs)
        else:
            await self._run(s_kwargs, e_kwargs, t_kwargs)

    # Start Block
    async def _start_async(self, s_kwargs: dict[str, Any] | None = None) -> None:
        """Starts the continuous execution of the block.

        Args:
            s_kwargs: The keyword arguments for block setup.
        """
        self._set_executing()

        # Optionally Setup
        if self.sets_up:
            await self.setup_async(**(s_kwargs or {}))

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
        """
        # Raise Error if the task is already running.
        if self.is_executing():
            raise RuntimeError(f"{self} task is already running.")

        # Setup IO and Start Proxy
        if as_proxy or (as_proxy is None and self.will_proxy) and not self.is_alive():
            self.start_io()
            self.actualize_io()
            self._start_server()
            self.finalize_io()
        else:
            self.actualize_io()
            if finalize:
                self.finalize_io()

        # Use Correct Context
        if self.is_alive():
            self._proxy.start(None, s_kwargs, False)
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
        """
        # Raise Error if the task is already running.
        if self.is_executing():
            raise RuntimeError(f"{self} task is already running.")

        # Setup IO and Start Proxy
        if as_proxy or (as_proxy is None and self.will_proxy) and not self.is_alive():
            await self.start_io_async()
            await self.actualize_io_async()
            self._start_server()
            await self.finalize_io_async()
        else:
            await self.actualize_io_async()
            if finalize:
                await self.finalize_io_async()

        # Use Correct Context
        if self.is_alive():
            await self._proxy.start_async(None, s_kwargs, False)
        else:
            await self._start_async(s_kwargs)

    # Stop Block
    async def _stop_block_async(
        self,
        t_kwargs: dict[str, Any] | None = None,
        join_io: bool = True,
        join_kwargs: dict[str, Any] | None = None,
        await_production: bool = True,
    ) -> None:
        # Join IO
        if join_io:
            await self.inputs.join_async(**(join_kwargs or {}))

        # Stop Production Task
        if self._production_task is not None:
            self.clear_loop_event()
            if await_production:
                await self._production_task
                self._production_task = None

        # Optionally Teardown
        if self.tears_down:
            await self.teardown_async(**(t_kwargs or {}))

        # Wait for any remaining Futures
        for future in self.futures:
            await future

        self._clear_executing()

    async def stop_block_async(
        self,
        t_kwargs: dict[str, Any] | None = None,
        join_io: bool = True,
        join_kwargs: dict[str, Any] | None = None,
        await_production: bool = True,
    ) -> None:
        await self._stop_block_async(t_kwargs, join_io, join_kwargs, await_production)
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
    ) -> None:
        """Stops the execution of this block, optionally stopping the server relative to this object.

        Args:
            server: Determines if the remote server should be stopped.
            update: Determines if this object should be updated from the server before stopping.
        """
        if self.is_alive() and server:
            self._proxy.stop_block_async(t_kwargs, join_io, join_kwargs, await_production)
            if update:
                self.join_execution()
            self._stop_server(update)
        elif (loop := self.async_event_loop) is not None:
            run_coroutine_threadsafe(self._stop_block_async(t_kwargs, join_io, join_kwargs, await_production), loop)
            self.inputs.stop()
            self.outputs.stop()
        else:
            run(self._stop_block_async(t_kwargs, join_io, join_kwargs, await_production))
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
    ) -> None:
        """Asynchronously Stops the execution of this block, optionally stopping the server relative to this object.

        Args:
            server: Determines if the remote server should be stopped.
            update: Determines if this object should be updated from the server before stopping.
        """
        if self.is_alive() and server:
            await self._proxy.stop_block_async(t_kwargs, join_io, join_kwargs, await_production)
            if update:
                await self.join_execution_async()
            await self._stop_server_async(update)
        else:
            await self._stop_block_async(t_kwargs, join_io, join_kwargs, await_production)
            await gather(*(self.inputs.stop_async(), self.outputs.stop_async()))

    # Join Execution
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

    async def join_execution_async(self, timeout: float | None = None, interval: float = 0.0) -> None:
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
            finally:
                self._executing_waiters.remove(fut)
