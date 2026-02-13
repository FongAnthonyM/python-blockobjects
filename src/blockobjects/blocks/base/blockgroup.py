"""blockgroup.py
Summary.

"""

# Header #
__package_name__ = "blockobjects"

__author__ = "Anthony Fong"
__credits__ = ["Anthony Fong"]
__copyright__ = "Copyright 2022, Anthony Fong"
__license__ = "MIT"

__version__ = "0.1.0"


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
from baseobjects.functions import MethodMultiplexer
from ...process import ProcessArbitrator, arbitratemethod
from ...process.context import BaseProcessingContext, ContextualEvent

# Local Packages #
from ...io import BaseIO, ArbitratingIOManager, IOWrapper, IORouter
from ...io.containers import IOQueue
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
        default_input_names: The default ordered tuple with the names of the inputs to an Block.
        default_output_names: The default ordered tuple with the names of the outputs to an Block.

    Attributes:
        inputs: The inputs manager of the Block.
        outputs: The outputs manager of the Block.
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
        "get_inner_proxies",
        "get_inner_proxies_async",
        "update_inner_proxies",
        "update_inner_proxies_async",
        "update_inner_io_proxies",
        "update_inner_io_proxies_async",
        "build_arbitrated_inputs",
        "build_arbitrated_inputs_async",
        "get_arbitrated_io",
        "get_arbitrated_io_async",
        "put_arbitrated_io",
        "put_arbitrated_io_async",
        "start_inner_proxies",
        "start_inner_proxies_async",
    }

    _default_input_signal_names: ClassVar[tuple[str, ...]] = ("stop_flag", "inner_stop_flag")

    init_blocks: ClassVar[bool] = True
    init_io_links: ClassVar[bool] = True

    # Attributes #
    will_evaluate: bool = False

    _signal_callback_map_ = {
        "stop_callback": {"method": "stop_signal", "signals": ("stop_flag",)},
        "inner_stop_callback": {"method": "inner_stop_signal", "signals": ("inner_stop_flag",)},
    }

    sets_up_inner_io_links: bool = True
    lazy_inner_io: bool = True
    lazy_finalize: bool = True

    wrapped_getter: str | None = None
    wrapped_getter_async: str | None = None
    wrapped_putter: str | None = "put_to_io"
    wrapped_putter_async: str | None = "put_to_io_async"
    arbitrated_io: dict[str, IOWrapper]

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
        init_io_links: bool | None = None,
        link_kwargs: dict[str, Any] | None = None,
        start_server: bool = False,
        proxy_context: BaseProcessingContext | None = None,
        _state: dict[str, Any] | None = None,
        init: bool = True,
        **kwargs: Any,
    ) -> None:
        # New Attributes #
        self.arbitrated_io = {}

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
                init_io_links=init_io_links,
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
        init_io_links: bool | None = None,
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
            self.create_blocks(**self.create_blocks_kwargs)

        if _state is None and (init_io_links or (init_io_links is None and self.init_io_links)):
            self.link_inner_io(**self.create_links_kwargs)

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

    def start_blocks(self) -> None:
        for block in self.blocks.values():
            if block.inputs.will_proxy:
                block.inputs.start_server()
            if block.outputs.will_proxy:
                block.outputs.start_server()

        for block in self.blocks.values():
            block.start()

    # IO
    def build_inner_io(self, *args: Any, override: bool = False, **kwargs: Any) -> None:
        """Builds the inner blockgroup' IO with new routing to properly link with other blockgroup' IO.

        Args:
            *args: The arguments for creating the inner blockgroup.
            override: Determines if the inner blockgroup will be overridden.
            **kwargs: The keyword arguments for creating the inner blockgroup.
        """

    def link_inner_io(self, *args: Any, **kwargs: Any) -> None:
        """Links the inner blockgroup' IO.

        Args:
            *args: The arguments for creating linking the inner blockgroup' IO.
            **kwargs: The keyword arguments for creating linking the inner blockgroup' IO.
        """

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

    def _build_inner_arbitrated_io(self, io_router: IORouter, inner_io: dict[int, IORouter]) -> None:
        for key, other in io_router.get_links_to().items():
            _, source, other_id, destination = key
            other_io = io_router[source]
            if (io_ := inner_io.get(other_id, None)) is not None and (not other.is_proxy() and not other.will_proxy):
                self.arbitrated_io[key] = io_.create_io_wrapper(destination)
                scheduled_listeners = io_.scheduled_listener_links
                if key in scheduled_listeners:
                    scheduled_listeners.discard(key)
            elif isinstance(other_io, IORouter):
                self._build_inner_arbitrated_io(other_io, inner_io)

    async def _build_inner_arbitrated_io_async(self, io_router: IORouter, inner_io: dict[int, IORouter]) -> None:
        links_to = await io_router.get_links_to_async()
        inner_coros = deque()
        for key, other in links_to.items():
            _, source, other_id, destination = key
            other_io = io_router[source]
            if (io_ := inner_io.get(other_id, None)) is not None and (not other.is_proxy() and not other.will_proxy):
                self.arbitrated_io[key] = io_.create_io_wrapper(destination)
                scheduled_listeners = io_.scheduled_listener_links
                if key in scheduled_listeners:
                    scheduled_listeners.discard(key)
            elif isinstance(other_io, IORouter):
                inner_coros.append(self._build_inner_arbitrated_io_async(other_io, inner_io))
        await gather(*inner_coros)

    def build_arbitrated_inputs(self) -> None:
        self._build_inner_arbitrated_io(self.inputs, self.get_inner_io_id())

    async def build_arbitrated_inputs_async(self) -> None:
        await self._build_inner_arbitrated_io_async(self.inputs, await self.get_inner_io_id_async())

    def get_arbitrated_io(self, key, value, *args: Any, **kwargs: Any) -> None:
        self.arbitrated_io[key].get(value, *args, **kwargs)

    async def get_arbitrated_io_async(self, key, value, *args: Any, **kwargs: Any) -> None:
        await self.arbitrated_io[key].get_async(value, *args, **kwargs)

    def put_arbitrated_io(self, key, value, *args: Any, **kwargs: Any) -> None:
        self.arbitrated_io[key].put(value, *args, **kwargs)

    async def put_arbitrated_io_async(self, key, value, *args: Any, **kwargs: Any) -> None:
        await self.arbitrated_io[key].put_async(value, *args, **kwargs)

    def _create_arbitrate_io_proxy_partial(self, part: partial, key: tuple) -> partial:
        """Creates a partial function which calls a proxy's arbitrate_io method with the link key fixed.

        This is a helper method used to create a flattened partial method using the original partial method -
        arbitrate_io - and the additional arguments need to have a fixed key. Since, at the time of writing, partial
        does not flatten properly when chained.

        Args:
            part: The original partial proxy arbitrate_io method that needs the key to be fixed.
            key: The key used for arbitrating the IO.

        Returns:
            A new partial proxy arbitrate_io method with the key fixed.
        """
        return partial(part.func.__func__, self._proxy, *part.args, key, **part.keywords)

    def create_arbitrate_io_wrapper(self, key: tuple) -> IOWrapper:
        if self.is_alive():
            getter = self._create_arbitrate_io_proxy_partial(self._proxy.get_arbitrated_io, key)
            getter_async = self._create_arbitrate_io_proxy_partial(self._proxy.get_arbitrated_io_async, key)
            putter = self._create_arbitrate_io_proxy_partial(self._proxy.put_arbitrated_io, key)
            putter_async = self._create_arbitrate_io_proxy_partial(self._proxy.put_arbitrated_io_async, key)
        else:
            getter = partial(self.get_arbitrated_io, key)
            getter_async = partial(self.get_arbitrated_io_async, key)
            putter = partial(self.put_arbitrated_io, key)
            putter_async = partial(self.put_arbitrated_io_async, key)

        return IOWrapper(getter, getter_async, putter, putter_async)

    def _set_arbitrated_io_links(
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
                top_io.set_recursive(inner_keys, self.create_arbitrate_io_wrapper(key))
            elif isinstance(other_io, IORouter):
                self._set_arbitrated_io_links(other_io, inner_io, top_io, inner_keys)

    async def _set_arbitrated_io_links_async(
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
                inner_coros.append(top_io.set_recursive_async(inner_keys, self.create_arbitrate_io_wrapper(key)))
            elif isinstance(other_io, IORouter):
                inner_coros.append(self._set_arbitrated_io_links_async(other_io, inner_io, top_io, inner_keys))
        await gather(*inner_coros)

    def set_arbitrated_input_links(self) -> None:
        self._set_arbitrated_io_links(self.inputs, self.get_inner_io_id(), self.inputs, ())

    async def set_arbitrated_input_links_async(self) -> None:
        await self._set_arbitrated_io_links_async(self.inputs, await self.get_inner_io_id_async(), self.inputs, ())

    def correct_input_links(self, *args: Any, **kwargs: Any) -> None:
        self.build_arbitrated_inputs()
        self.set_arbitrated_input_links()

    async def correct_input_links_async(self, *args: Any, **kwargs: Any) -> None:
        await self.build_arbitrated_inputs_async()
        await self.set_arbitrated_input_links_async()

    def get_inner_proxies(self) -> dict[str, Any]:
        return {n: b.get_proxy() for n, b in self.blocks.items() if b.is_alive()}

    async def get_inner_proxies_async(self) -> dict[str, Any]:
        return {n: b.get_proxy() for n, b in self.blocks.items() if b.is_alive()}

    def get_proxies(self) -> dict[str, Any]:
        proxies = super().get_proxies()
        proxies["inner"] = self.get_inner_proxies()
        return proxies

    async def get_proxies_async(self) -> dict[str, Any]:
        proxies = await super().get_proxies_async()
        proxies["inner"] = await self.get_inner_proxies_async()
        return proxies

    def set_inner_proxies(self, proxies: dict[str, Any]) -> None:
        for name, proxies in proxies.items():
            self.blocks[name].set_proxies(proxies)

    async def set_inner_proxies_async(self, proxies: dict[str, Any]) -> None:
        await gather(*(self.blocks[n].set_proxies_async(p) for n, p in proxies.items()))

    def set_proxies(self, proxies: dict[str, Any]) -> None:
        super().set_proxies(proxies)
        self.set_inner_proxies(proxies["inner"])

    async def set_proxies_async(self, proxies: dict[str, Any]) -> None:
        await gather(super().set_proxies_async(proxies), self.set_inner_proxies_async(proxies["inner"]))

    def update_inner_proxies(self) -> dict[str, Any]:
        return {n: b.update_proxies() for n, b in self.blocks.items() if b.is_alive()}

    async def update_inner_proxies_async(self) -> dict[str, Any]:
        names = tuple(self.blocks.keys())
        coro_iter = (self.blocks[n].update_proxies_async() for n in names if self.blocks[n].is_alive())
        return dict(zip(names, await gather(*coro_iter)))

    def update_proxies(self) -> dict[str, Any]:
        proxies = super().get_proxies()
        inner_proxies = self.update_inner_proxies()
        self.set_inner_proxies(inner_proxies)
        proxies["inner"] = inner_proxies
        return proxies

    async def update_proxies_async(self) -> dict[str, Any]:
        proxies = await super().update_proxies_async()
        inner_proxies = await self.update_inner_proxies_async()
        await self.set_inner_proxies_async(inner_proxies)
        proxies["inner"] = inner_proxies
        return proxies

    def update_inner_io_proxies(self) -> None:
        """Updates both the inner inputs' and outputs' proxies to match the current state."""
        for block in self.blocks.values():
            block.update_io_proxies()

    async def update_inner_io_proxies_async(self) -> None:
        """Asynchronously updates both the inner inputs' and outputs' proxies to match the current state.'"""
        if self.blocks:
            await gather(*(b.update_io_proxies_async() for b in self.blocks.values()))

    def update_io_proxies(self) -> None:
        """Updates both the inputs' and outputs' proxies to match the current state."""
        super().update_io_proxies()
        self.update_inner_io_proxies()

    async def update_io_proxies_async(self) -> None:
        """Asynchronously updates both the inputs' and outputs' proxies to match the current state.'"""
        await gather(super().update_io_proxies_async(), self.update_inner_io_proxies_async())

    def finalize_inner_io(self) -> None:
        for block in self.blocks.values():
            block.finalize_io()

    async def finalize_inner_io_async(self) -> None:
        if self.blocks:
            await gather(*(b.finalize_io_async() for b in self.blocks.values()))

    def finalize_io(self) -> None:
        """Finalizes the inputs and outputs before starting the block."""
        self.correct_input_links()
        self.finalize_inner_io()
        super().finalize_io()

    async def finalize_io_async(self) -> None:
        """Asynchronously finalizes the inputs and outputs before starting the block."""
        if self.is_alive():
            await self.correct_input_links_async()
        await self.finalize_inner_io_async()
        await super().finalize_io_async()

    # Signals
    def stop_signal(self, stop_flag: bool) -> None:
        raise NotImplementedError

    async def stop_signal_async(self, stop_flag: bool) -> None:
        raise NotImplementedError

    def inner_stop_signal(self, stop_flag: bool) -> None:
        if stop_flag:
            self.stop_as_task(stop_inner=False)

    async def inner_stop_signal_async(self, stop_flag: bool) -> None:
        if stop_flag:
            self.stop_as_task(stop_inner=False)

    # Evaluate
    def evaluate(self, *args: Any, **kwargs: Any) -> Any:
        """An abstract method which is the evaluation of this object.

        Args:
            *args: The arguments for evaluating.
            **kwargs: The keyword arguments for evaluating.

        Returns:
            The result of the evaluation.
        """
        raise NotImplementedError

    # Start Proxy
    def start_inner_proxies(self, update_local: bool = False, update_io: bool = False) -> None:
        for block in self.blocks.values():
            if block.will_proxy:
                block.start_proxy(update_local=update_local, update_io=update_io)

    async def start_inner_proxies_async(self, update_local: bool = False, update_io: bool = False) -> None:
        coros = deque()
        for block in self.blocks.values():
            if block.will_proxy:
                coros.append(block.start_proxy_async(update_local=update_local, update_io=update_io))
        await gather(*coros)

    def start_proxy(self, as_proxy: bool | None = None, update_local: bool = True, update_io: bool = True) -> None:
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
            # Finalize IO
            self.finalize_io()

        # Start Inner Proxies
        self.start_inner_proxies()

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
        update_local: bool = True,
        update_io: bool = True,
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
            # Finalize IO
            await self.finalize_io_async()

        # Start Inner Proxies
        await self.start_inner_proxies_async()

        # Update Proxy References
        if update_local:
            # Cascade update all the proxies so they have the references/links to the other proxies.
            await self.update_proxies_async()

        # Update IO
        if update_io:
            # Cascade update all the IO objects so they have the references/link to the other proxies.
            await self.update_io_proxies_async()

    # Start
    async def _start_async(self, s_kwargs: dict[str, Any] | None = None) -> None:
        """Starts the continuous execution of the block.

        Args:
            s_kwargs: The keyword arguments for block setup.
        """
        self._set_executing()

        # Optionally Setup
        await self.ensure_setup_async(**(s_kwargs or {}))

        # Start Inner Blocks
        if self.will_evaluate:
            await gather(*(block.ensure_setup_async() for block in self.blocks.values()))
        else:
            await gather(*(block.start_async(finalize=False) for block in self.blocks.values()))

    # Stop Block Execution
    async def _stop_block_async(
        self,
        join_io: bool = True,
        await_production: bool = True,
        stop_inner: bool | None = None,
        join_kwargs: dict[str, Any] | None = None,
        t_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Stops the continuous execution of the block.

        Args:
            t_kwargs: The keyword arguments for block teardown.
        """
        # Join IO
        if join_io:
            await self.inputs.join_all_async(**(join_kwargs or {}))

        # Stop Production Task
        if self._production_task is not None:
            self.clear_loop_event()
            if await_production:
                await self._production_task
                self._production_task = None

        # Stop Inner Blocks
        if stop_inner or (stop_inner is None and not self.will_evaluate):
            await gather(*(block.stop_async() for block in self.blocks.values()))

        # Optionally Teardown
        await self.ensure_teardown_async(**(t_kwargs or {}))

        # Wait for any remaining Futures
        for future in self.futures:
            await future

        self._clear_executing()

    # Join
    async def join_stop_task_async(self, timeout: float | None = None) -> None:
        tasks = deque((create_task(super().join_stop_task(timeout)),))
        for block in self.blocks.values():
            tasks.append(create_task(block.join_stop_task(timeout)))

        await wait_for(gather(*tasks), timeout)

    async def join_async(self, timeout: float | None = None, join_self: bool = False) -> None:
        tasks = deque()
        for block in self.blocks.values():
            tasks.append(create_task(block.join_async(timeout)))

        if join_self:
            tasks.append(create_task(super().join_async(timeout)))

        await wait_for(gather(*tasks), timeout)
