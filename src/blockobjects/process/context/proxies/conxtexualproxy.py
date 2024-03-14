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
from collections.abc import Iterable
from typing import Any

# Third-Party Packages #

# Local Packages #
from ..baseprocessingcontext import BaseProcessingContext
from ..contextualobject import ContextualObject
from .proxyinterface import ProxyInterface


# Definitions #
# Classes #
class ContextualProxy(ContextualObject, ProxyInterface):

    # Class Attributes
    _proxy_classes: dict[type, dict[tuple[str, tuple], type]] = {}
    _exposed_: set = set()

    # Class Methods
    @classmethod
    def get_exposed(cls, target_cls: type, exposed: Iterable[str] | None = None) -> set[str]:
        exposed = set(exposed or ())
        c_exposed = set(getattr(target_cls, "exposed", ()))
        p_exposed = cls._exposed_
        return exposed | c_exposed | p_exposed

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
            dic = {}
            for meth in exposed:
                exec('''def %s(self, /, *args, **kwds):
                    return gettattr(self._proxy, %r)(*args, **kwds)''' % (meth, meth), dic)

            proxy_classes[key] = proxy_class = type(name, (cls,), dic)
            proxy_class._exposed_ = exposed

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
        return proxy_type(cls=cls, args=args, kwargs=kwargs, **_kwargs)

    # Attributes #
    _proxy: ProxyInterface | None

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        proxy: ProxyInterface | None = None,
        cls=None,
        args=None,
        kwargs=None,
        *,
        context: BaseProcessingContext | None = None,
        init: bool = True,
    ) -> None:
        # Attributes #

        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct(proxy=proxy, cls=cls, args=args, kwargs=kwargs, context=context)

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        proxy: ProxyInterface | None = None,
        cls=None,
        args=None,
        kwargs=None,
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
            self._proxy = self.context.create_proxy(name=str(id(self)), cls=cls, args=args, kwargs=kwargs)

    # State
    @abstractmethod
    def is_alive(self) -> bool:
        pass

    # Execution
    @abstractmethod
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
