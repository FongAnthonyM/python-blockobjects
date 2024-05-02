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
from asyncio import gather
from asyncio.events import AbstractEventLoop, get_event_loop, _get_running_loop
from abc import abstractmethod
from collections.abc import Iterable, Mapping
from collections import deque
from contextlib import contextmanager
from functools import partial
from time import perf_counter
from typing import ClassVar, Any
from warnings import warn

# Third-Party Packages #
from baseobjects.collections import OrderableDict
from baseobjects.functions import CallableMultiplexObject, MethodMultiplexer
from ...process import ProcessDelegate, delegatemethod
from ...process.context import BaseProcessingContext, ContextualEvent

# Local Packages #
from ...io import DelegatingIOManager, IOWrapper, IORouter
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
    exposed: ClassVar[set] = BaseBlock.exposed | {"put_to_io", "put_to_io_async"}

    init_blocks: ClassVar[bool] = True

    # Attributes #
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
        self.inputs.wrapped_getter_async = "put_item_async"

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

    def construct_blocks(
        self,
        create_kwargs: dict[str, Any] | None = None,
        link_kwargs: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        self.create_blocks(**(create_kwargs or {}))
        self.link_inner_io(**(link_kwargs or {}))
        self.lazy_blocks = False

    def start_blocks_passive(self) -> None:
        for block in self.blocks.values():
            if block.inputs.will_proxy:
                block.inputs.start_server()
            if block.outputs.will_proxy:
                block.outputs.start_server()

        for block in self.blocks.values():
            block.start_passive()

    # IO
    def link_inner_io(self, *args: Any, **kwargs: Any) -> None:
        """Links the inner blocks' IO.

        Args:
            *args: The arguments for creating linking the inner blocks' IO.
            **kwargs: The keyword arguments for creating linking the inner blocks' IO.
        """

    def start_inner_inputs(self) -> None:
        for block in self.blocks.values():
            block.start_inputs()

    def start_inner_outputs(self) -> None:
        for block in self.blocks.values():
            block.start_outputs()

    def start_inner_io(self) -> None:
        for block in self.blocks.values():
            block.start_io()

    def materialize_inner_io(self) -> None:
        for block in self.blocks.values():
            block.materialize_io()

    def put_to_io(self, key, value, *args: Any, **kwargs: Any) -> None:
        self.delegated_io[key].put(value, *args, **kwargs)

    async def put_to_io_async(self, key, value, *args: Any, **kwargs: Any) -> None:
        await self.delegated_io[key].put_async(value, *args, **kwargs)

    def create_io_wrapper(self, key: tuple, io_: IOWrapper,  *args: Any, **kwargs: Any) -> IOWrapper:
        self.delegated_io[key] = io_

        getter = None if self.wrapped_getter is None else partial(getattr(self, self.wrapped_getter), key)
        if self.wrapped_getter_async is None:
            getter_async = None
        else:
            getter_async = partial(getattr(self, self.wrapped_getter_async), key)

        putter = None if self.wrapped_putter is None else partial(getattr(self, self.wrapped_putter), key)
        if self.wrapped_putter_async is None:
            putter_async = None
        else:
            putter_async = partial(getattr(self, self.wrapped_putter_async), key)

        return IOWrapper(getter, getter_async, putter, putter_async)

    def _correct_input_links(self, io_router: IORouter):
        for key, (source, other, destination) in io_router.items():
            io_ = io_router[source]
            if isinstance(io_, IORouter):
                self._correct_input_links(io_)
            else:
                if not other.is_proxy() and not other.will_proxy:
                    io_router[source] = self.create_io_wrapper(key, io_)

    def correct_input_links(self, *args: Any, **kwargs: Any) -> None:
        self._correct_input_links(self.inputs)

    def finalize_inner_io(self) -> None:
        self.start_io()
        self.start_inner_io()
        self.materialize_io()
        self.materialize_inner_io()
        if self.will_proxy or self.inputs.is_proxy() or self.inputs.will_proxy:
            self.correct_input_links()
            if self.inputs.is_proxy():
                self.inputs.update_server_io()
        self.lazy_finalize = False

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
            block.execute()

    # Start Passive
    async def _start_passive(self, s_kwargs: dict[str, Any] | None = None) -> None:
        """Starts the continuous execution of the block.

        Args:
            s_kwargs: The keyword arguments for block setup.
        """
        self._set_executing()

        # Optionally Creates Blocks
        if self.lazy_blocks:
            self.construct_blocks(self.create_blocks_kwargs, self.create_links_kwargs)
            self.lazy_finalize = True

        if self.lazy_finalize:
            self.finalize_inner_io()

        # Optionally Setup
        if self.sets_up:
            await self.setup_async(**(s_kwargs or {}))

        # Start Inner Blocks
        await gather(*(block.start_passive_async(finalize=False) for block in self.blocks.values()))

    # Stop Block Passive Execution
    async def _stop_passive(self, t_kwargs: dict[str, Any] | None = None) -> None:
        """Starts the continuous execution of the block.

        Args:
            t_kwargs: The keyword arguments for block teardown.
        """
        # Stop Inner Blocks
        await gather(*(block.stop_passive_async() for block in self.blocks.values()))

        # Optionally Teardown
        if self.tears_down:
            await self.teardown_async(**(t_kwargs or {}))

        # Wait for any remaining Futures
        for future in self.futures:
            await future

        self._clear_executing()
