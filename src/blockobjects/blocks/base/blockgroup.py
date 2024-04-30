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
from asyncio import run, Future, Task, create_task, run_coroutine_threadsafe, iscoroutinefunction, wait_for
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

    # Attributes #
    wrapped_getter: str | None = None
    wrapped_getter_async: str | None = None
    wrapped_putter: str | None = "put_to_io"
    wrapped_putter_async: str | None = "put_to_io_async"
    delegated_io: dict[str, IOWrapper]

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
        start_server: bool = False,
        proxy_context: BaseProcessingContext | None = None,
        _state: dict[str, Any] | None = None,
        init: bool = True,
        **kwargs: Any,
    ) -> None:
        # New Attributes #
        self.delegated_io = {}

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
        self.outputs.create_link.select("create_link_none")

        if blocks is not None:
            self.blocks.update(blocks)

        # Construct Parent #
        super().construct(
            *args,
            will_proxy=will_proxy,
            init_io=init_io,
            init_setup=init_setup,
            setup_kwargs=setup_kwargs,
            start_server=start_server,
            proxy_context=proxy_context,
            _state=_state,
            **kwargs,
        )

    # Blocks
    def create_blocks(self, *args: Any, override: bool = False, **kwargs: Any) -> None:
        """Creates the inner blocks.

        Args:
            *args: The arguments for creating the inner blocks.
            override: Determines if the inner blocks will be overridden.
            **kwargs: The keyword arguments for creating the inner blocks.
        """

    def start_blocks_passive(self) -> None:
        for block in self.blocks.values():
            if block.inputs.will_proxy:
                block.inputs.start_server()
            if block.outputs.will_proxy:
                block.outputs.start_server()

        for block in self.blocks.values():
            block.start_passive()

    # IO
    def start_inputs(self) -> None:
        super().start_inputs()
        for block in self.blocks.values():
            block.start_inputs()

    def start_outputs(self) -> None:
        super().start_outputs()
        for block in self.blocks.values():
            block.start_outputs()

    def materialize_io_links(self) -> None:
        super().materialize_io_links()
        for block in self.blocks.values():
            block.materialize_io_links()

    def link_inner_io(self, *args: Any, **kwargs: Any) -> None:
        """Links the inner blocks' IO.

        Args:
            *args: The arguments for creating linking the inner blocks' IO.
            **kwargs: The keyword arguments for creating linking the inner blocks' IO.
        """

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

    # Setup
    def setup(
        self,
        *args: Any,
        create: bool = True,
        create_kwargs: dict[str, Any] | None = None,
        link: bool = True,
        link_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Creates the inner blocks and links their IO.

        Args:
            *args: The arguments for setup.
            create: Determines if the inner block will be created.
            create_kwargs: The keyword arguments for creating the inner blocks.
            link: Determines if the inner IO will be linked between blocks.
            link_kwargs: The keyword arguments for creating linking the inner blocks' IO.
            **kwargs: The keyword arguments for setup.
        """
        if self.setup_kwargs is not None and (c_kwargs := self.setup_kwargs.get("create_kwargs")) is not None:
            create_kwargs = c_kwargs | (create_kwargs if create_kwargs is not None else {})
        elif create_kwargs is None:
            create_kwargs = {}

        if create:
            self.create_blocks(**create_kwargs)

        if self.setup_kwargs is not None and (l_kwargs := self.setup_kwargs.get("link_kwargs")) is not None:
            link_kwargs = l_kwargs | (link_kwargs if link_kwargs is not None else {})
        elif link_kwargs is None:
            link_kwargs = {}

        if link:
            self.link_inner_io(**(link_kwargs if link_kwargs is not None else {}))
            if self.will_proxy or self.inputs.is_proxy() or self.inputs.will_proxy:
                self.correct_input_links()
                if self.inputs.is_proxy():
                    self.inputs.update_server_io()

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
        for operation in self.operations.values():
            operation.execute()
