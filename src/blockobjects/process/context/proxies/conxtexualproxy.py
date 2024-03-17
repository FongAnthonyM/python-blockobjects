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
from abc import abstractmethod
from collections.abc import Iterable, Generator
from typing import Any, ClassVar

# Third-Party Packages #
from baseobjects.typing import AnyCallable

# Local Packages #
from ..baseprocessingcontext import BaseProcessingContext
from ..contextualobject import ContextualObject
from ..interfaces import ProxyInterface


# Definitions #
# Classes #
class ContextualProxy(ContextualObject, ProxyInterface):

    # Class Attributes
    _proxy_classes: ClassVar[dict[type, dict[tuple[str, tuple], type]]] = {}
    _exposed_: ClassVar[set] = set()
    _unexposed_: ClassVar[set] = set()
    exposed: ClassVar[set]

    # Class Methods
    @classmethod
    def iter_method_names(cls, obj) -> Generator[str, None, None]:
        return (name for name in dir(obj) if callable(getattr(obj, name)))

    @classmethod
    def iter_public_method_names(cls, obj) -> Generator[str, None, None]:
        return (name for name in cls.iter_method_names(obj) if name[0] != '_')

    @classmethod
    def get_exposed(cls, target_cls: type, exposed: Iterable[str] | None = None) -> set[str]:
        public_methods = set(cls.iter_public_method_names(target_cls))
        exposed = set(exposed or ())
        c_exposed = set(getattr(target_cls, "exposed", ()))
        c_unexposed = set(getattr(target_cls, "unexposed", ()))
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
        def func_(obj, *args, **kwargs):
            """Evaluates the wrapped object's method."""
            return getattr(obj._proxy, name)(*args, **kwargs)

        return func_

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
            proxy_class.exposed = set(exposed)

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
    ) -> None:
        # Attributes #

        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct(
                proxy=proxy,
                cls=cls,
                args=args,
                kwargs=kwargs,
                c_cls=c_cls,
                exposed=exposed,
                context=context,
            )

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        proxy: ProxyInterface | None = None,
        cls=None,
        args=None,
        kwargs=None,
        c_cls=None,
        exposed: Iterable[str] | None = None,
        *,
        context: BaseProcessingContext | None = None,
    ) -> None:
        """Constructs this object.

        Args:
            context: The context of this Queue.
        """
        if proxy is not None:
            self._proxy = proxy

        super().construct(context=context)

        if self._proxy is None and context is not None:
            self._proxy = self.context.create_proxy(
                name=str(id(self)),
                cls=cls,
                args=args,
                kwargs=kwargs,
                c_cls=c_cls,
                exposed=exposed,
            )

    # State
    #@abstractmethod
    def is_alive(self) -> bool:
        pass

    # Execution
    #@abstractmethod
    async def execute_remote(self, name, args=(), kwargs={}) -> Any:
        pass

    # Context
    def set_context(self, context: BaseProcessingContext) -> None:
        """Sets the context of this object to the given context.

        Args:
            context: The context to assign this object to.
        """
        super().set_context(context=context)

        # Create a new queue and move the contents to the new queue
        new_proxy = context.require_proxy(name=str(id(self)))
        self._proxy = new_proxy
