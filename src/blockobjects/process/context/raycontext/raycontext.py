"""raycontext.py
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
from typing import Any

# Third-Party Packages #
from baseobjects.functions import BaseDecorator
from ray import remote, method
from ray.actor import ActorClass

# Local Packages #
from ...interfaces import LockInterface, EventInterface, QueueInterface, ProxyInterface
from ..bases import BaseProcessingContext
from ..managercontext import ManagerContext
from .synchronize import RayLock, RayEvent
from .queues import RayQueue
from .proxies import RayProxy


# Definitions #
# Functions #
def _setstate_(self, state: dict[str, Any]) -> None:
    """Builds this object based on a dictionary of corresponding attributes.

    Args:
        state: The attributes to build this object from.
    """
    self.__dict__.update(state)


# Classes #
class RayContext(BaseProcessingContext):
    """A ProcessContext for Ray.

    Attributes:
        lock_type: The type of lock to create when creating locks.
        event_type: The type of event to create when creating events.
        queue_type: The type of queue to create when creating queues.
        simple_queue_type: The type of simple queue to create when creating simple queues.
    """
    # Class Methods #

    # Attributes #
    lock_type: type[LockInterface] = RayLock
    event_type: type[EventInterface] = RayEvent
    queue_type: type[QueueInterface] = RayQueue
    simple_queue_type: type[QueueInterface] = RayQueue
    proxy_type: type[ProxyInterface] = RayProxy

    actor_class_register: dict[type, ActorClass]

    # Magic Methods  #
    # Construction/Destruction
    def __init__(self, init: bool = True) -> None:
        # Attributes #
        self.actor_class_register = {}

        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct()

    # Instance Methods #
    # Proxies
    def create_actor_class(self, cls: type, **kwargs: Any) -> ActorClass:
        self.actor_class_register[cls] = a_cls = remote(**kwargs)(cls) if kwargs else remote(cls)
        return a_cls

    def require_actor_class(self, cls: type, **kwargs: Any) -> ActorClass:
        if (a_cls := self.actor_class_register.get(cls, None)) is None:
            self.actor_class_register[cls] = a_cls = remote(**kwargs)(cls) if kwargs else remote(cls)
        return a_cls

    def create_proxy(
        self,
        name=None,
        cls=None,
        args=(),
        kwargs=None,
        *_args,
        c_cls=None,
        exposed=None,
        **_kwargs,
    ) -> ProxyInterface:
        """Creates and adds a proxy to the context's object register.

        Args:
            name: The name of the remote proxy to create.
            cls: The class type of the remote proxy to create.
            args: The arguments for creating the remote proxy.
            kwargs: The keyword arguments for creating the remote proxy.
            manager_type: The type of multiprocessing manager to use to create the proxy.
            manager: The multiprocessing manager to use to create the proxy.

        Returns:
            The proxy.
        """
        if c_cls is None:
            c_cls = self.proxy_type

        if (a_cls := self.actor_class_register.get(cls, None)) is None:
            exp = c_cls.get_exposed(cls, exposed)
            w_cls = type(f"{cls.__name__}ActorWrapper", (cls,), {})
            if hasattr(cls, "__class_getitem__"):
                w_cls.__class_getitem__ = None
            for n, decorator in ((n, d) for n in exp if isinstance(d := getattr(w_cls, n), BaseDecorator)):
                setattr(w_cls, n, decorator.as_function())
            self.actor_class_register[cls] = a_cls = remote(**_kwargs)(w_cls) if _kwargs else remote(w_cls)
            _kwargs = {}

        proxy = c_cls.new_actor_proxy(cls, a_cls, args, kwargs=kwargs, exposed=exposed)

        self.object_register["proxies"][(str(id(proxy)) if name is None else name)] = proxy
        return proxy
