""" rayproxy.py

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
from asyncio import iscoroutinefunction, wrap_future
from collections.abc import Iterable, Generator
from functools import partialmethod
from typing import Any, ClassVar

# Third-Party Packages #
from baseobjects.typing import AnyCallable
from baseobjects.operations import iter_public_method_names
import ray
from ray import get, kill, ObjectRef
from ray.actor import ActorClass, ActorHandle

# Local Packages #
from ....interfaces import ProxyInterface


# Definitions #
# Classes #
class RayProxy(ProxyInterface):

    # Static Methods #
    @staticmethod
    def _call_inner_method(obj, name, *args, **kwargs):
        """Evaluates the wrapped object's method."""
        return getattr(obj._actor, name).remote(*args, **kwargs)

    @staticmethod
    def _call_inner_method_get(obj, name, *args, **kwargs):
        """Evaluates the wrapped object's method."""
        return get(getattr(obj._actor, name).remote(*args, **kwargs))

    # Class Attributes #
    _proxy_classes: ClassVar[dict[type, dict[tuple[str, tuple], type]]] = {}
    _exposed_: ClassVar[set] = set()
    _unexposed_: ClassVar[set] = set()
    exposed: ClassVar[set]

    # Class Methods
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
    def _create_proxy_method(cls, name: str, is_coro: bool) -> AnyCallable:
        """A factory for creating method functions for accessing a proxy's methods.

        Args:
            name: The name of the method

        Returns:
            The function for a method.
        """
        return partialmethod(cls._call_inner_method if is_coro else cls._call_inner_method_get, name)

    @classmethod
    def create_proxy_type(cls, target_cls: type, name: str, exposed: Iterable[str]) -> type:
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
                is_coro = iscoroutinefunction(getattr(target_cls, name))
                setattr(proxy_class, name, cls._create_proxy_method(name, is_coro))
                # if not is_coro and (a_name := f"{name}_async") in exposed:
                #     setattr(proxy_class, name, cls._create_proxy_method(a_name, False))
                # else:
                #     setattr(proxy_class, name, cls._create_proxy_method(name, is_coro))
            proxy_class.exposed = set(exposed)

        # Return Proxy Class
        return proxy_class

    @classmethod
    def new_actor_proxy(
        cls,
        target_cls: type,
        actor_cls: ActorClass,
        args=(),
        kwargs=None,
        *_args,
        exposed: Iterable[str] | None = None,
        **_kwargs,
    ) -> "RayProxy":
        # Create Proxy Type
        name = f"AutoRayProxy{target_cls.__name__}"
        exposed = cls.get_exposed(target_cls=target_cls, exposed=exposed)
        proxy_type = cls.create_proxy_type(target_cls=target_cls, name=name, exposed=exposed)

        # Return Proxy
        return proxy_type(cls=actor_cls, args=args, kwargs=kwargs, exposed=exposed, **_kwargs)

    # Attributes #
    _actor_class: ActorClass | None = None
    _actor: ActorHandle | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        actor: ActorHandle | None = None,
        cls: ActorClass | None = None,
        args: Iterable[Any] = (),
        kwargs: dict[str, Any] | None = None,
        *,
        exposed: Iterable[str] | None = None,
        init: bool = True,
    ) -> None:
        # Attributes #

        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.__construct(
                actor=actor,
                cls=cls,
                args=args,
                kwargs=kwargs,
                exposed=exposed,
            )

    # Instance Methods #
    # Constructors/Destructors
    def __construct(
        self,
        actor: ActorHandle | None = None,
        cls: ActorClass | None = None,
        args: Iterable[Any] = (),
        kwargs: dict[str, Any] | None = None,
        *,
        exposed: Iterable[str] | None = None,
        **_kwargs: Any,
    ) -> None:
        """Constructs this object.

        Args:
            context: The context of this Queue.
        """
        if cls is not None:
            self._actor_class = cls

        if actor is not None:
            self._actor = actor

        super().construct()

        if self._actor is None and self._actor_class is not None:
            if _kwargs:
                self._actor_ = self._actor_class.options(**_kwargs).remote(*args, **kwargs)
            else:
                self._actor = self._actor_class.remote(*args, **kwargs)

    # State
    def _is_alive(self) -> bool:
        """Returns True if the proxy server is alive, False otherwise."""
        return self._actor is not None

    def _kill_server(self) -> None:
        """Kills the server which the proxy is running on."""
        kill(self._actor)
        self._actor = None
