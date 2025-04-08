""" arbitratingiomanager.py
An IO object which maps named inputs to names outputs in a one-to-one manner.
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
from collections.abc import Iterable, MutableMapping
from functools import partial
from typing import ClassVar, Any

# Third-Party Packages #
import dill
from baseobjects import BaseMethod
from ...process import ProcessArbitrator, arbitratemethod

# Local Packages #
from ..base import BaseIO, IOWrapper
from .contextualiomanager import ContextualIOManager


# Definitions #
# Classes #
class ArbitratingIOManager(ContextualIOManager, ProcessArbitrator):
    """An IO object which maps named inputs to names outputs in a one-to-one manner.

    Class Attributes:
        default_get: The default name of the method to use for getting.
        default_put: The default name of the method to use for putting.

    Attributes:
        get: The method multiplexer which manages which get method to run when called.
        put: The method multiplexer which manages which get method to run when called.
        default_io: The default IO object type to populate this object when constructed.

    Args:
        io_: The input/outputs to be managed.
        *args: Arguments for inheritance.
        init: Determines if this object will construct.
        **kwargs: Keyword arguments for inheritance.
    """

    # Class Attributes #
    _memory_deletables: tuple = ("links_to", "links_from", "endpoints")
    unexposed: ClassVar[set] = {
        "is_endpoint_link",
        "is_listen_link",
        "default_io_type",
        "create_io_wrapper",
        "create_encapsulated_proxy_wrapper",
    }
    local_methods: ClassVar[set] = {
        "create_io_wrapper",
        "link_forward",
        "link_backward",
        "update_server_io",
        "update_server_io_async",
        "create_io_wrapper_parent",
        "provide_io_wrapper",
        "provide_io_wrapper_async",
    }

    default_get: ClassVar[str] = "get_groups"
    default_get_async: ClassVar[str] = "get_groups_async"
    default_put: ClassVar[str] = "put_ordered"
    default_put_async: ClassVar[str] = "put_ordered_async"
    default_create_link: ClassVar[str] = "create_io_wrapper"

    # Attributes #
    # State
    will_proxy: bool = False

    # Pickling
    def __getstate__(self) -> dict[str, Any]:
        """Creates a dictionary of attributes which can be used to rebuild this object.

        Returns:
            A dictionary of this object's attributes.
        """
        state = super().__getstate__()
        # Save memory by deleting large unused attributes.
        if self.is_alive():
            for name in self._memory_deletables:
                if name in state:
                    del state[name]

        return state

    # Wrapper
    def create_io_wrapper(self, name: str, *args: Any, **kwargs: Any) -> IOWrapper:
        obj = self._proxy or self

        getter = None if self.wrapped_getter is None else partial(getattr(obj, self.wrapped_getter), name)
        if self.wrapped_getter_async is None:
            getter_async = None
        else:
            getter_async = partial(getattr(obj, self.wrapped_getter_async), name)

        putter = None if self.wrapped_putter is None else partial(getattr(obj, self.wrapped_putter), name)
        if self.wrapped_putter_async is None:
            putter_async = None
        else:
            putter_async = partial(getattr(obj, self.wrapped_putter_async), name)

        return IOWrapper(getter, getter_async, putter, putter_async)

    def set_encapsulated_wrapper(self, key, *args: Any, **kwargs: Any) -> None:
        self.encapsulated_wrappers[key] = self.create_io_wrapper(*args, **kwargs)

    async def set_encapsulated_wrapper_async(self, key, *args: Any, **kwargs: Any) -> None:
        self.encapsulated_wrappers[key] = self.create_io_wrapper(*args, **kwargs)

    def create_encapsulated_proxy_wrapper(self, key, proxy, *args, **kwargs) -> IOWrapper:
        getter = partial(proxy.encapsulated_get, key, *args, **kwargs)
        getter_async = partial(proxy.encapsulated_get_async, key, *args, **kwargs)
        putter = partial(proxy.encapsulated_put, key, *args, **kwargs)
        putter_async = partial(proxy.encapsulated_put_async, key, *args, **kwargs)
        joiner = partial(proxy.encapsulated_join, key, *args, **kwargs)
        joiner_async = partial(proxy.encapsulated_join_async, key, *args, **kwargs)

        return IOWrapper(getter, getter_async, putter, putter_async, joiner, joiner_async)

    def create_io_wrapper_parent(
        self,
        key,
        *args: Any,
        e_args: Iterable[Any, ...] = (),
        e_kwargs: MutableMapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> BaseIO:
        if (proxy := self._proxy) is not None:
            self.set_encapsulated_wrapper(key, *args, **kwargs)
            return self.create_encapsulated_proxy_wrapper(key, proxy, *e_args, **(e_kwargs or {}))
        else:
            return super().create_io_wrapper_parent(key, *args, e_args=e_args, e_kwargs=e_kwargs, **kwargs)

    def provide_io_wrapper(
        self,
        key,
        *args: Any,
        e_args: Iterable[Any, ...] = (),
        e_kwargs: MutableMapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> BaseIO:
        if (proxy := self._proxy) is not None:
            if self.parent is not None:
                self.set_encapsulated_wrapper(key, *args, **kwargs)
                return self.create_encapsulated_proxy_wrapper(key, proxy, *e_args, **(e_kwargs or {}))
            else:
                return self.create_io_wrapper(*args, **kwargs)
        else:
            return super().provide_io_wrapper(key, *args, e_args=e_args, e_kwargs=e_kwargs, **kwargs)

    async def provide_io_wrapper_async(
        self,
        key,
        *args: Any,
        e_args: Iterable[Any, ...] = (),
        e_kwargs: MutableMapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> BaseIO:
        if (proxy := self._proxy) is not None:
            if self.parent is not None:
                await self.set_encapsulated_wrapper_async(key, *args, **kwargs)
                return self.create_encapsulated_proxy_wrapper(key, proxy, *e_args, **(e_kwargs or {}))
            else:
                return self.create_io_wrapper(*args, **kwargs)
        else:
            return await super().provide_io_wrapper_async(key, *args, e_args=e_args, e_kwargs=e_kwargs, **kwargs)


    # Linking
    def is_remote(self) -> bool:
        return self.is_alive() or self.will_proxy

    def update_server_io(self):
        self._proxy.set_deepest(super().get_deepest())

    async def update_server_io_async(self):
        await self._proxy.set_deepest_async(super().get_deepest())

    # Proxy
    def _stop_server(self, update: bool = True, exclude: set | None = None) -> None:
        """Stops the remote server relative to this object.

        Args:
            update: Determines if this object should be updated from the server before stopping.
        """
        self.stop()
        super()._stop_server(update, exclude)
