""" blockgroup.py

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
from asyncio import gather, Future, Task, create_task, run_coroutine_threadsafe, iscoroutinefunction, wait_for
from asyncio.events import AbstractEventLoop, get_event_loop, _get_running_loop
from abc import abstractmethod
from collections.abc import Iterable, Mapping
from collections import deque
from contextlib import contextmanager
from functools import partial, partialmethod
from time import perf_counter
from types import MethodType
from typing import ClassVar, Any
from warnings import warn

# Third-Party Packages #
from baseobjects.collections import OrderableDict
from baseobjects.functions import CallableMultiplexObject, MethodMultiplexer
from ...process import ProcessDelegate, delegatemethod
from ...process.context import BaseProcessingContext, ContextualEvent

# Local Packages #
from ...io import BaseIO, DelegatingIOManager, IOWrapper, IORouter
from .baseblock import BaseBlock


# Definitions #
# Classes #
class BlockGroup(BaseBlock):
    """A Block which contains several Block objects to execute.

    BlockGroup is more of an abstract class because IO and contained Blocks must be defined, but an
    BlockGroup object can still function properly without defining those.

    The IO and/or contained Blocks can be defined in either the "construction_io" or the "setup" methods. Blocks
    could also be defined outside the BlockGroup class and be added into the OrderableDict "block" directly.

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
        blocks: The ordered dictionary of Block to execute and the order to execute them in.

    Args:
        blocks: The dictionary of Block to add to the BlockGroup.
        *args: Arguments for inheritance.
        init_io: Determines if construct_io run during this construction.
        sets_up: Determines if setup will run during this construction.
        setup_kwargs: The keyword arguments for the setup method.
        init: Determines if this object will construct.
        **kwargs: Keyword arguments for inheritance.
    """
    # Class Attributes #
    exposed: ClassVar[set] = BaseBlock.exposed | {
        "create_blocks",
        "create_blocks_async",
        "link_inner_io",
        "link_inner_io_async",
        "build_delegated_inputs",
        "build_delegated_inputs_async",
        "get_delegated_io",
        "get_delegated_io_async",
        "put_delegated_io",
        "put_delegated_io_async",
    }

    init_blocks: ClassVar[bool] = True

    # Attributes #
    sets_up_blocks: bool = True
    lazy_blocks: bool = True
    lazy_finalize: bool = True

    wrapped_getter: str | None = None
    wrapped_getter_async: str | None = None
    wrapped_putter: str | None = "put_to_io"
    wrapped_putter_async: str | None = "put_to_io_async"
    delegated_io: dict[str, IOWrapper]

    create_links_kwargs: dict[str, Any] = {}

    create_blocks_kwargs: dict[str, Any] = {}
    blocks: OrderableDict[str, BaseBlock]

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        blocks: Mapping[str, BaseBlock] | None = None,
        *args: Any,
        will_proxy: bool | None = None,
        will_produce: bool | None = None,
        init_io: bool = True,
        init_setup: bool | None = None,
        setup_kwargs: dict[str, Any] | None = None,
        init_blocks: bool | None = None,
        create_kwargs: dict[str, Any] | None = None,
        link_kwargs: dict[str, Any] | None = None,
        start_server: bool = False,
        proxy_context: BaseProcessingContext | None = None,
        _state: dict[str, Any] | None = None,
        init: bool = True,
        **kwargs: Any,
    ) -> None:
        # New Attributes #
        self.delegated_io = {}

        self.create_links_kwargs = self.create_links_kwargs.copy()

        self.create_blocks_kwargs = self.create_blocks_kwargs.copy()
        self.blocks = OrderableDict()

        # Parent Attributes #
        super().__init__(*args, init=False, **kwargs)

        # Construct #
        if init:
            self.construct(
                blocks,
                *args,
                will_proxy=will_proxy,
                will_produce=will_produce,
                init_io=init_io,
                init_setup=init_setup,
                setup_kwargs=setup_kwargs,
                init_blocks=init_blocks,
                create_kwargs=create_kwargs,
                link_kwargs=link_kwargs,
                start_server=start_server,
                proxy_context=proxy_context,
                _state=_state,
                **kwargs,
            )

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        blocks: Mapping[str, BaseBlock] | None = None,
        *args: Any,
        will_proxy: bool | None = None,
        will_produce: bool | None = None,
        init_io: bool = True,
        init_setup: bool | None = None,
        setup_kwargs: dict[str, Any] | None = None,
        init_blocks: bool | None = None,
        create_kwargs: dict[str, Any] | None = None,
        link_kwargs: dict[str, Any] | None = None,
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
        self.inputs.wrapped_putter = "put_item"
        self.inputs.wrapped_putter_async = "put_item_async"
        self.outputs.wrapped_putter = "put_item"
        self.outputs.wrapped_putter_async = "put_item_async"

        if blocks is not None:
            self.blocks.update(blocks)

        # Construct Parent #
        super().construct(
            *args,
            will_proxy=will_proxy,
            init_io=init_io,
            init_setup=False,
            setup_kwargs=setup_kwargs,
            start_server=start_server,
            proxy_context=proxy_context,
            _state=_state,
            **kwargs,
        )

        if create_kwargs is not None:
            self.create_blocks_kwargs.update(create_kwargs)

        if link_kwargs is not None:
            self.create_links_kwargs.update(link_kwargs)

        if _state is None and (init_blocks or (init_blocks is None and self.init_blocks)):
            self.construct_blocks(self.create_blocks_kwargs, self.create_links_kwargs)

        if _state is None and (init_setup or (init_setup is None and self.init_setup)):
            self.setup(**({} if setup_kwargs is None else setup_kwargs))

    # Blocks
    def create_blocks(self, *args: Any, override: bool = False, **kwargs: Any) -> None:
        """Creates the inner blocks.

        Args:
            *args: The arguments for creating the inner blocks.
            override: Determines if the inner blocks will be overridden.
            **kwargs: The keyword arguments for creating the inner blocks.
        """

    async def create_blocks_async(self, *args: Any, override: bool = False, **kwargs: Any) -> None:
        return self.create_blocks(*args, override=override, **kwargs)

    def setup_blocks(self, *args: Any, **kwargs: Any) -> None:
        if self.sets_up_blocks:
            self.create_blocks(*args, **kwargs)
            self.sets_up_blocks = False

    async def setup_blocks_async(self, *args: Any, **kwargs: Any) -> None:
        if self.sets_up_blocks:
            await self.create_blocks_async(*args, **kwargs)
            self.sets_up_blocks = False

    def construct_blocks(
        self,
        create_kwargs: dict[str, Any] | None = None,
        link_kwargs: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.setup_blocks(**(create_kwargs or {}))
        self.link_inner_io(**(link_kwargs or {}))
        self.lazy_blocks = False

    def start_blocks_passive(self) -> None:
        for block in self.blocks.values():
            if block.inputs.will_proxy:
                block.inputs.start_server()
            if block.outputs.will_proxy:
                block.outputs.start_server()

        for block in self.blocks.values():
            block.start()

    # IO
    def link_inner_io(self, *args: Any, **kwargs: Any) -> None:
        """Links the inner blocks' IO.

        Args:
            *args: The arguments for creating linking the inner blocks' IO.
            **kwargs: The keyword arguments for creating linking the inner blocks' IO.
        """

    async def link_inner_io_async(self, *args: Any, **kwargs: Any) -> Any:
        return self.link_inner_io(*args, **kwargs)

    def get_inner_io_id(self) -> dict[int, IORouter]:
        io_ = {}
        for block in self.blocks.values():
            io_[block.inputs.get_id_number()] = block.inputs
            io_[block.outputs.get_id_number()] = block.outputs
        return io_

    async def get_inner_io_id_async(self) -> dict[int, IORouter]:
        coros = deque()
        ids = deque()
        for block in self.blocks.values():
            coros.append(block.inputs.get_id_number_async())
            ids.append(block.inputs)
            coros.append(block.outputs.get_id_number_async())
            ids.append(block.outputs)
        return dict(zip(await gather(*coros), ids))

    def start_inner_inputs(self) -> None:
        for block in self.blocks.values():
            block.start_inputs()

    async def start_inner_inputs_async(self) -> None:
        await gather(*(block.start_inputs_async() for block in self.blocks.values()))

    def start_inner_outputs(self) -> None:
        for block in self.blocks.values():
            block.start_outputs()

    async def start_inner_outputs_async(self) -> None:
        await gather(*(block.start_outputs_async() for block in self.blocks.values()))

    def start_inner_io(self) -> None:
        for block in self.blocks.values():
            block.start_io()

    async def start_inner_io_async(self) -> None:
        await gather(*(block.start_io_async() for block in self.blocks.values()))

    def materialize_inner_io(self) -> None:
        for block in self.blocks.values():
            block.materialize_io()

    async def materialize_inner_io_async(self) -> None:
        await gather(*(block.materialize_io_async() for block in self.blocks.values()))

    def setup_inner_io(self) -> None:
        for block in self.blocks.values():
            block.setup_io()

    async def setup_inner_io_async(self) -> None:
        await gather(*(block.setup_io_async() for block in self.blocks.values()))

    def _build_inner_delegated_io(self, io_router: IORouter, inner_io: dict[int, IORouter]) -> None:
        for key, other in io_router.get_links_to().items():
            _, source, other_id, destination = key
            other_io = io_router[source]
            if (io_ := inner_io.get(other_id, None)) is not None and (not other.is_proxy() and not other.will_proxy):
                self.delegated_io[key] = io_.create_io_wrapper(destination)
                scheduled_listeners = io_.scheduled_listener_links
                if key in scheduled_listeners:
                    scheduled_listeners.discard(key)
            elif isinstance(other_io, IORouter):
                self._build_inner_delegated_io(other_io, inner_io)

    async def _build_inner_delegated_io_async(self, io_router: IORouter, inner_io: dict[int, IORouter]) -> None:
        links_to = await io_router.get_links_to_async()
        inner_coros = deque()
        for key, other in links_to.items():
            _, source, other_id, destination = key
            other_io = io_router[source]
            if (io_ := inner_io.get(other_id, None)) is not None and (not other.is_proxy() and not other.will_proxy):
                self.delegated_io[key] = io_.create_io_wrapper(destination)
                scheduled_listeners = io_.scheduled_listener_links
                if key in scheduled_listeners:
                    scheduled_listeners.discard(key)
            elif isinstance(other_io, IORouter):
                inner_coros.append(self._build_inner_delegated_io_async(other_io, inner_io))
        await gather(*inner_coros)

    def build_delegated_inputs(self) -> None:
        self._build_inner_delegated_io(self.inputs, self.get_inner_io_id())

    async def build_delegated_inputs_async(self) -> None:
        await self._build_inner_delegated_io_async(self.inputs, await self.get_inner_io_id_async())

    def get_delegated_io(self, key, value, *args: Any, **kwargs: Any) -> None:
        self.delegated_io[key].get(value, *args, **kwargs)

    async def get_delegated_io_async(self, key, value, *args: Any, **kwargs: Any) -> None:
        await self.delegated_io[key].get_async(value, *args, **kwargs)

    def put_delegated_io(self, key, value, *args: Any, **kwargs: Any) -> None:
        self.delegated_io[key].put(value, *args, **kwargs)

    async def put_delegated_io_async(self, key, value, *args: Any, **kwargs: Any) -> None:
        await self.delegated_io[key].put_async(value, *args, **kwargs)

    def _create_delegate_io_proxy_partial(self, part: partial, key: tuple) -> partial:
        """Creates a partial function which calls a proxy's delegate_io method with the link key fixed.

        This is a helper method used to create a flattened partial method using the original partial method -
        delegate_io - and the additional arguments need to have a fixed key. Since, at the time of writing, partial
        does not flatten properly when chained.

        Args:
            part: The original partial proxy delegate_io method that needs the key to be fixed.
            key: The key used for delegating the IO.

        Returns:
            A new partial proxy delegate_io method with the key fixed.
        """
        return partial(part.func.__func__, self._proxy, *part.args, key, **part.keywords)

    def create_delegate_io_wrapper(self, key: tuple) -> IOWrapper:
        if self.is_alive():
            getter = self._create_delegate_io_proxy_partial(self._proxy.get_delegated_io, key)
            getter_async = self._create_delegate_io_proxy_partial(self._proxy.get_delegated_io_async, key)
            putter = self._create_delegate_io_proxy_partial(self._proxy.put_delegated_io, key)
            putter_async = self._create_delegate_io_proxy_partial(self._proxy.put_delegated_io_async, key)
        else:
            getter = partial(self.get_delegated_io, key)
            getter_async = partial(self.get_delegated_io_async, key)
            putter = partial(self.put_delegated_io, key)
            putter_async = partial(self.put_delegated_io_async, key)

        return IOWrapper(getter, getter_async, putter, putter_async)

    def _set_delegated_io_links(
        self,
        io_router: IORouter,
        inner_io: dict[int, IORouter],
        top_io: IORouter,
        keys: tuple[str, ...],
    ) -> None:
        for key, other in io_router.get_links_to().items():
            _, source, other_id, destination = key
            inner_keys = keys + (source,)
            other_io = io_router[source]
            if other_id in inner_io and (not other.is_proxy() and not other.will_proxy):
                top_io.set_recursive(inner_keys, self.create_delegate_io_wrapper(key))
            elif isinstance(other_io, IORouter):
                self._set_delegated_io_links(other_io, inner_io, top_io, inner_keys)

    async def _set_delegated_io_links_async(
        self,
        io_router: IORouter,
        inner_io: dict[int, IORouter],
        top_io: IORouter,
        keys: tuple[str, ...],
    ) -> None:
        links_to = await io_router.get_links_to_async()
        inner_coros = deque()
        for key, other in links_to.items():
            _, source, other_id, destination = key
            inner_keys = keys + (source,)
            other_io = io_router[source]
            if other_id in inner_io and (not other.is_proxy() and not other.will_proxy):
                inner_coros.append(top_io.set_recursive_async(inner_keys, self.create_delegate_io_wrapper(key)))
            elif isinstance(other_io, IORouter):
                inner_coros.append(self._set_delegated_io_links_async(other_io, inner_io, top_io, inner_keys))
        await gather(*inner_coros)

    def set_delegated_input_links(self) -> None:
        self._set_delegated_io_links(self.inputs, self.get_inner_io_id(), self.inputs, ())

    async def set_delegated_input_links_async(self) -> None:
        await self._set_delegated_io_links_async(self.inputs, await self.get_inner_io_id_async(), self.inputs, ())

    def correct_input_links(self, *args: Any, **kwargs: Any) -> None:
        self.build_delegated_inputs()
        self.set_delegated_input_links()

    async def correct_input_links_async(self, *args: Any, **kwargs: Any) -> None:
        await self.build_delegated_inputs_async()
        await self.set_delegated_input_links_async()

    def finalize_io(self) -> None:
        self.correct_input_links()
        self.set_input_callback()
        self.inputs.start_listeners()
        self.outputs.start_listeners()

    async def finalize_io_async(self) -> None:
        if self.is_alive():
            await self.correct_input_links_async()
        await self.set_input_callback_async()
        await self.inputs.start_listeners_async()
        await self.outputs.start_listeners_async()

    def setup_io(self) -> None:
        if self.sets_up_io:
            if self.inputs.is_proxy():
                self.inputs.update()
            if self.outputs.is_proxy():
                self.outputs.update()

            self.link_inner_io()
            self.start_inner_io()
            self.setup_inner_io()

            if self.inputs.is_proxy():
                self.inputs.update_server_io()
            if self.outputs.is_proxy():
                self.outputs.update_server_io()

            self.sets_up_io = False

    async def setup_io_async(self) -> None:
        if self.sets_up_io:
            if self.inputs.is_proxy():
                await self.inputs.update_async()
            if self.outputs.is_proxy():
                await self.outputs.update_async()

            await self.link_inner_io_async()
            await self.start_inner_io_async()
            await self.setup_inner_io_async()

            if self.inputs.is_proxy():
                await self.inputs.update_server_io_async()
            if self.outputs.is_proxy():
                await self.outputs.update_server_io_async()

            self.sets_up_io = False

    # Evaluate
    def evaluate(self, *args: Any, **kwargs: Any) -> Any:
        """An abstract method which is the evaluation of this object.

        Args:
            *args: The arguments for evaluating.
            **kwargs: The keyword arguments for evaluating.

        Returns:
            The result of the evaluation.
        """
        self.inputs.put_all(**kwargs)
        outputs = self.outputs.get_all()
        match len(outputs):
            case 0:
                return None
            case 1:
                return outputs[0]
            case _:
                return outputs

    async def evaluate_async(self, *args: Any, **kwargs: Any) -> Any:
        """An abstract method which is the evaluation of this object.

        Args:
            *args: The arguments for evaluating.
            **kwargs: The keyword arguments for evaluating.

        Returns:
            The result of the evaluation.
        """
        await self.inputs.put_all_async(**kwargs)
        outputs = await self.outputs.get_all_async()
        match len(outputs):
            case 0:
                return None
            case 1:
                return outputs[0]
            case _:
                return outputs

    # Execute
    def execute_all(self) -> None:
        """Executes all operation within this operation group."""
        for block in self.blocks.values():
            block.full_execute()

    # Start Passive
    async def _start_async(self, s_kwargs: dict[str, Any] | None = None) -> None:
        """Starts the continuous execution of the block.

        Args:
            s_kwargs: The keyword arguments for block setup.
        """
        self._set_executing()

        # Optionally Setup
        if self.sets_up:
            await self.setup_async(**(s_kwargs or {}))

        # Start Inner Blocks
        await gather(*(block.start_async() for block in self.blocks.values()))

    def start(
        self,
        as_proxy: bool | None = None,
        s_kwargs: dict[str, Any] | None = None,
        finalize: bool = True,
    ) -> None:
        """Starts the continuous execution of the block, delegating to another process if selected.

        Args:
            as_proxy: Determines if this object should run in a separate process.
            s_kwargs: The keyword arguments for block setup.
        """
        # Raise Error if the task is already running.
        if self.is_executing():
            raise RuntimeError(f"{self} task is already running.")

        # Setup IO and Start Proxy
        if as_proxy or (as_proxy is None and self.will_proxy) and not self.is_alive():
            self.setup_blocks()
            self.start_io()
            self.setup_io()
            self._start_server()
            self.finalize_io()
        else:
            self.setup_blocks()
            self.setup_io()
            if finalize:
                self.finalize_io()

        # Use Correct Context
        if self.is_alive():
            self._proxy.start_passive(None, s_kwargs, False)
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
        """Asynchronously starts the continuous execution of the block, delegating to another process if selected.

        Args:
            as_proxy: Determines if this object should run in a separate process.
            s_kwargs: The keyword arguments for block setup.
        """
        # Raise Error if the task is already running.
        if self.is_executing():
            raise RuntimeError(f"{self} task is already running.")

        # Setup IO and Start Proxy
        if as_proxy or (as_proxy is None and self.will_proxy) and not self.is_alive():
            await self.setup_blocks_async()
            await self.start_io_async()
            await self.setup_io_async()
            self._start_server()
            await self.finalize_io_async()
        else:
            await self.setup_blocks_async()
            await self.setup_io_async()
            if finalize:
                await self.finalize_io_async()

        # Use Correct Context
        if self.is_alive():
            await self._proxy.start_async(None, s_kwargs, False)
        else:
            await self._start_async(s_kwargs)

    # Stop Block Passive Execution
    async def _stop_async(self, t_kwargs: dict[str, Any] | None = None) -> None:
        """Starts the continuous execution of the block.

        Args:
            t_kwargs: The keyword arguments for block teardown.
        """
        # Stop Inner Blocks
        await gather(*(block.stop_async() for block in self.blocks.values()))

        # Optionally Teardown
        if self.tears_down:
            await self.teardown_async(**(t_kwargs or {}))

        # Wait for any remaining Futures
        for future in self.futures:
            await future

        self._clear_executing()
