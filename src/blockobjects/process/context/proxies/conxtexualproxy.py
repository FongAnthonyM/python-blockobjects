""" contextualproxy.py

"""
# Package Header #
from ....header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Standard Libraries #
from collections.abc import Iterable, Generator
from functools import partialmethod
from typing import Any, ClassVar

# Third-Party Packages #
from baseobjects.typing import AnyCallable
from baseobjects.operations import iter_public_method_names

# Local Packages #
from ..bases import BaseProcessingContext
from ..contextualobject import ContextualObjectInterface
from ..interfaces import ProxyInterface


# Definitions #
# Classes #
def rebuild_proxy(cls, name, proxy, exposed, context):
    ProxyType = cls.create_proxy_type(name, exposed)
    return None if proxy is None else ProxyType(proxy, context=context)


class ContextualProxy(ContextualObjectInterface, ProxyInterface):

    # Static Methods #
    @staticmethod
    def _call_inner_method(obj, name, *args, **kwargs):
        """Evaluates the wrapped object's method."""
        return getattr(obj._proxy, name)(*args, **kwargs)

    # Class Attributes #
    _proxy_classes: ClassVar[dict[type, dict[tuple[str, tuple], type]]] = {}
    _exposed_: ClassVar[set] = set()
    _unexposed_: ClassVar[set] = set()
    exposed: ClassVar[set]
    __exposed__: ClassVar[set]

    # Class Methods #
    @classmethod
    def get_exposed(cls, target_cls: type, exposed: Iterable[str] | None = None) -> set[str]:
        public_methods = set(iter_public_method_names(target_cls))
        exposed = set(exposed or ())
        c_exposed = set(getattr(target_cls, "exposed", ())) | set(getattr(target_cls, "_exposed_", ()))
        c_unexposed = set(getattr(target_cls, "unexposed", ())) | set(getattr(target_cls, "_unexposed_", ()))
        p_exposed = cls._exposed_
        p_unexposed = cls._unexposed_
        return (public_methods | exposed | c_exposed | p_exposed) - c_unexposed - p_unexposed

    @classmethod
    def _create_proxy_method(cls, name: str) -> AnyCallable:
        """A factory for creating method functions for accessing a proxy's methods.

        Args:
            name: The name of the method

        Returns:
            The function for a method.
        """
        return partialmethod(cls._call_inner_method, name)

    @classmethod
    def create_proxy_type(cls, name: str, exposed: Iterable[str]) -> type:
        # Create Storage Key
        exposed = tuple(exposed)
        key = (name, exposed)

        # Get Class Register
        if (proxy_classes := cls._proxy_classes.get(cls, None)) is None:
            cls._proxy_classes[cls] = proxy_classes = {}

        # Create and Register Class if it does not exist
        if (proxy_class := proxy_classes.get(key, None)) is None:
            proxy_classes[key] = proxy_class = type(name, (cls,), {})
            for name in exposed:
                setattr(proxy_class, name, cls._create_proxy_method(name))
            proxy_class.__exposed__ = set(exposed)

        # Return Proxy Class
        return proxy_class

    @classmethod
    def new_proxy(
        cls,
        target_cls: type,
        args=(),
        kwargs=None,
        *_args,
        exposed: Iterable[str] | None = None,
        **_kwargs,
    ) -> "ContextualProxy":
        # Create Proxy Type
        name = f"AutoContextualProxy{target_cls.__name__}"
        exposed = cls.get_exposed(target_cls=target_cls, exposed=exposed)
        proxy_type = cls.create_proxy_type(name=name, exposed=exposed)

        # Return Proxy
        return proxy_type(cls=target_cls, args=args, kwargs=kwargs, exposed=exposed, **_kwargs)

    # Attributes #
    __context: BaseProcessingContext | None = None
    _proxy: ProxyInterface | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        proxy: ProxyInterface | None = None,
        cls=None,
        args=None,
        kwargs=None,
        *,
        c_cls=None,
        exposed: Iterable[str] | None = None,
        context: BaseProcessingContext | None = None,
        init: bool = True,
        **_kwargs: Any,
    ) -> None:
        # Attributes #

        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.__construct(
                proxy=proxy,
                cls=cls,
                args=args,
                kwargs=kwargs,
                c_cls=c_cls,
                exposed=exposed,
                context=context,
                **_kwargs,
            )

    # Pickling
    def __reduce__(self) -> tuple:
        args = (ContextualProxy, self.__class__.__name__, self._proxy, self.__exposed__, self.__context)
        return rebuild_proxy, args

    def __getstate__(self) -> dict[str, Any]:
        """Creates a dictionary of attributes which can be used to rebuild this object.

        Returns:
            A dictionary of this object's attributes.
        """
        state = super().__getstate__()
        if "__context" not in state:
            state["__context"] = self.__context
        return state

    # Instance Methods #
    # Constructors/Destructors
    def __construct(
        self,
        proxy: ProxyInterface | None = None,
        cls=None,
        args=None,
        kwargs=None,
        c_cls=None,
        exposed: Iterable[str] | None = None,
        *,
        context: BaseProcessingContext | None = None,
        **_kwargs: Any,
    ) -> None:
        """Constructs this object.

        Args:
            context: The context of this Queue.
        """
        if context is not None:
            self.__context = context

        if proxy is not None:
            self._proxy = proxy

        super().construct()

        if self._proxy is None and context is not None:
            self._proxy = self.__context.create_proxy(
                name=str(id(self)),
                cls=cls,
                args=args,
                kwargs=kwargs,
                c_cls=c_cls,
                exposed=exposed,
                **_kwargs,
            )

    # Context
    def __set_context(self, context: BaseProcessingContext) -> None:
        """Sets the context of this object to the given context.

        Args:
            context: The context to assign this object to.
        """
        self.__context = context

        # Create a new server and proxy
        new_proxy = context.require_proxy(name=str(id(self)))
        self._proxy = new_proxy

    # State
    def _is_alive(self) -> bool:
        """Returns True if the proxy server is alive, False otherwise."""
        return self._proxy is not None and self._proxy._is_alive()

    # Server
    def _kill_server(self) -> None:
        """Kills the server which the proxy is running on."""
        if self._proxy is not None and self._proxy._is_alive():
            self._proxy._kill_server()
