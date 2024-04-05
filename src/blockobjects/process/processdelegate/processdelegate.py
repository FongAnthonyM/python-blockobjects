""" processdelegate.py.py

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
from collections.abc import Iterable
from typing import Any, ClassVar

# Third-Party Packages #
from baseobjects import search_sentinel
from baseobjects.operations import iter_public_method_names

# Local Packages #
from ..context import BaseProcessingContext, BaseContextualObject, ProxyInterface
from .delegatemethod import delegatemethod


# Definitions #
# Classes #
class ProcessDelegate(BaseContextualObject):
    """

    Class Attributes:

    Attributes:

    Args:

    """

    # Class Attributes #
    public_exposed: ClassVar[bool] = True
    _exposed_: ClassVar[set] = set()
    exposed: ClassVar[set] = set()

    _unexposed_: ClassVar[set] = {"is_proxy", "is_alive",  "get_context", "set_context"}
    unexposed: ClassVar[set] = set()

    _local_: ClassVar[set] = {"stop_server", "set_server_state", "update", "update_server"}

    # Attributes #
    untransmittable: set = set()
    proxy_kwargs: dict[str, Any] = {}

    # Class Methods #
    @classmethod
    def _get_exposed(cls) -> set[str]:
        """Gets the exposed method names, methods that can be evaluated on remote server, of this class.

        Returns:
            The set of exposed method names.
        """
        public_methods = set(iter_public_method_names(cls)) if cls.public_exposed else set()
        return (public_methods | cls.exposed | cls._exposed_) - cls.unexposed - cls._unexposed_

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """The init when creating a subclass.

        Args:
            **kwargs: The keyword arguments for creating a subclass.
        """
        super.__init_subclass__()

        ignore = set()
        for name in cls._get_exposed():
            method = getattr(cls, name, None)
            if (
                not isinstance(method, delegatemethod) and
                not isinstance(getattr(method, "__func__", method), delegatemethod)
            ):
                wrapper_method = "local_call" if name in cls._local_ else delegatemethod._wrapper_method
                d_method = delegatemethod(method, wrapper_method=wrapper_method)
                setattr(cls, name, d_method)
                ignore.add(name)
        cls._exposed_done = ignore

    # Attributes
    _is_proxy: bool = False
    _proxy: ProxyInterface | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        *,
        start_server: bool = False,
        context: BaseProcessingContext | None = None,
        _state: dict[str, Any] | None = None,
        init: bool = True,
    ) -> None:
        # New Attributes #

        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct(start_server=start_server, context=context, _state=_state)

    # Pickling
    def __getstate__(self) -> dict[str, Any]:
        """Creates a dictionary of attributes which can be used to rebuild this object.

        Returns:
            A dictionary of this object's attributes.
        """
        state = super().__getstate__()
        for name in ("_proxy", "_is_proxy",):
            if name in state:
                del state[name]
        return state

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        *,
        start_server: bool = False,
        context: BaseProcessingContext | None = None,
        _state: dict[str, Any] | None = None,
    ) -> None:
        """Constructs this object.

        Args:
            start_server: Determines whether the server should be started during construction.
            context: The context of this Queue.
            _state: A dictionary of attributes which can be used to this object.
        """
        # Construct Parent
        super().construct(context=context)

        # Set State
        if _state:
            self.__setstate__(state=_state)
            self._is_proxy = False  # Ensure this object's proxy state is correct

        # Start Server
        if start_server:
            self._start_server()

    # Proxy and Server
    # State
    def is_proxy(self) -> bool:
        """Checks if this object is a proxy of another object on a remote server.

        Returns:
            True if this object is a proxy, False if this object is evaluating locally.
        """
        return self._is_proxy

    def is_alive(self) -> bool:
        """Checks if the remote server is alive.

        Returns:
            True if this object is alive, False if it is not alive.
        """
        return False if self._proxy is None else self._proxy._is_alive()

    # Getters/Setters
    def get_attribute(self, name: str, default: Any = search_sentinel) -> Any:
        """Get an attribute, delegated from either the local object or remote object.

        Args:
            name: The name of the attribute to get.
            default: The default value to return if the attribute does not exist.

        Returns:
            The requested attribute.
        """
        if default is not search_sentinel:
            return getattr(self, name, default)
        else:
            return getattr(self, name)

    def set_attribute(self, name: str, value: Any) -> None:
        """Delegated setting of an attribute in either the local object or remote object.

        Args:
            name: The name of the attribute to set.
            value: The value to set the attribute to.
        """
        setattr(self, name, value)

    def _get_state(self) -> dict[str, Any]:
        """Creates a dictionary of attributes, delegated from either the local object or remote object.

        Returns:
            A dictionary of this object's attributes.
        """
        state = self.__getstate__()
        for name in self.untransmittable:
            if name in state:
                del state[name]
        return state

    def get_state(self) -> dict[str, Any]:
        """Creates a dictionary of attributes, delegated from either the local object or remote object.

        Returns:
            A dictionary of this object's attributes.
        """
        return self._get_state()

    def _set_state(self, state: dict[str, Any]) -> None:
        """Delegated building of either the local object or remote object from dictionary of attributes.

        Args:
            state: The attributes to build this object from.
        """
        self.__setstate__(state)

    def set_state(self, state: dict[str, Any]) -> None:
        """Delegated building of either the local object or remote object from dictionary of attributes.

        Args:
            state: The attributes to build this object from.
        """
        self._set_state(state)

    def set_server_state(self, state: dict[str, Any]) -> None:
        """Builds the remote server object from dictionary of attributes.

        Args:
            state: The attributes to build this object from.
        """
        if self._is_proxy and (proxy := self._proxy) is not None and proxy._is_alive():
            proxy.set_state(state)
        else:
            raise RuntimeError("Sever process must be alive")

    def update(self) -> None:
        """Builds the local object from state of the remote server object."""
        if self._is_proxy:
            if (proxy := self._proxy) is not None and proxy._is_alive():
                self.__setstate__(proxy.get_state())
            else:
                raise RuntimeError("Remote process must be alive")

    def update_server(self) -> None:
        """Builds the remote server object from state of the local object."""
        if self._is_proxy:
            self.set_server_state(self._get_state())

    # Server Management
    def _start_server(self, args: tuple = (), kwargs: dict | None = None) -> None:
        """Starts the remote server relative to this object.

        Args:
            args: Arguments for creating the object on the server.
            kwargs: Keyword arguments for creating the object on the server.
        """
        # Ensure this object's attributes is passed to the server object
        if "_state" not in (kwargs := kwargs or {}):
            kwargs["_state"] = self.__getstate__()

        # Start Server by creating a proxy from the context
        self._proxy = self.context.create_proxy(cls=self.__class__, args=args, kwargs=kwargs, **self.proxy_kwargs)

        # Ensure that this object's state is a proxy
        self._is_proxy = True

    def start_server(self, args: tuple = (), kwargs: dict | None = None) -> None:
        """Starts a remote server. If called multiple times, it will recursively create more servers.

        Args:
            args: Arguments for creating the object on the server.
            kwargs: Keyword arguments for creating the object on the server.
        """
        self._start_server(args, kwargs)

    def _stop_server(self, update: bool = True) -> None:
        """Stops the remote server relative to this object.

        Args:
            update: Determines if this object should be updated from the server before stopping.
        """
        # Updates this object's attributes
        if update:
            self.update()

        # Remove the server (server should stop when de-referenced)
        self._proxy = None

        # Set this object's state is not a proxy
        self._is_proxy = False

    def stop_server(self, update: bool = True) -> None:
        """Stops a remote server. If called multiple times, it will recursively stop the deepest server.

        Args:
            update: Determines if this object should be updated from the server before stopping.
        """
        if self.is_proxy():
            if (proxy := self._proxy) is not None and proxy._is_alive():
                if proxy.get_attribute("_is_proxy"):
                    proxy.stop_sever(update)
                else:
                    self._stop_server(update)
            else:
                raise RuntimeError("Server process must be alive")

    # Processing Context
    def get_context(self) -> BaseProcessingContext:
        """Gets the context of this object.

        Returns:
            The context of this object.
        """
        return self._proxy.context if self._is_proxy else self._context

    def set_context(self, context: BaseProcessingContext) -> None:
        """Sets the context of this object to the given context.

        Args:
            context: The context to assign this object to.
        """
        super().set_context(context=context)

        # Create a new server and proxy
        if self._is_proxy:
            self.update()  # Update local attributes
            self.proxy.set_context(context)  # Set the proxy's context
            self.update_server()  # Update server attributes
