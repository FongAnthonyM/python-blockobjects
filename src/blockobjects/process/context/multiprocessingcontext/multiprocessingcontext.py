""" multiprocessingcontext.py

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
from typing import Any
from weakref import ref

# Third-Party Packages #
from multiprocessing.managers import BaseManager, BaseProxy

# Local Packages #
from ...interfaces import LockInterface, EventInterface, QueueInterface, ProxyInterface
from ..bases import BaseProcessingContext
from ..managercontext import ManagerContext
from .synchronize import MultiProcessingLock, MultiProcessingEvent
from .queues import MultiProcessingQueue, MultiProcessingSimpleQueue
from .proxies import MultiprocessingProxyServer


# Definitions #
# Classes #
class MultiProcessingContext(BaseProcessingContext):
    """A ProcessContext for python's multiprocessing library.

    Attributes:
        lock_type: The type of lock to create when creating locks.
        event_type: The type of event to create when creating events.
        queue_type: The type of queue to create when creating queues.
        simple_queue_type: The type of simple queue to create when creating simple queues.
    """
    # Attributes #
    lock_type: type[LockInterface] = MultiProcessingLock
    event_type: type[EventInterface] = MultiProcessingEvent
    queue_type: type[QueueInterface] = MultiProcessingQueue
    simple_queue_type: type[QueueInterface] = MultiProcessingSimpleQueue

    default_manager_type: BaseManager = MultiprocessingProxyServer
    manager_types: dict[str, type[BaseManager]]
    managers: dict[str, BaseManager]
    proxy_register: dict[str, tuple[BaseProxy, BaseManager, type[BaseManager]]]

    # Magic Methods  #
    # Construction/Destruction
    def __init__(self, init: bool = True) -> None:
        # Attributes #
        self.manager_types = {}
        self.managers = {}
        self.proxy_register = {}

        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct()

    # Pickling
    def __getstate__(self) -> dict[str, Any]:
        """Creates a dictionary of attributes which can be used to rebuild this object.

        Returns:
            A dictionary of this object's attributes.
        """
        state = super().__getstate__()
        del state["managers"], state["proxy_register"]
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Builds this object based on a dictionary of corresponding attributes.

        Args:
            state: The attributes to build this object from.
        """
        super().__setstate__(state)
        self.managers = {}
        self.proxy_register = {}

    # Instance Methods #
    # Proxies
    def register_manager(
        self,
        name: str,
        manager: BaseManager | None = None,
        manager_type: type[BaseManager] | None = None,
    ) -> None:
        """Registers a manager and/or manager type to a class name to use for creating proxies.

        Args:
            name: The name of the class to register the manager to.
            manager: The manager to register.
            manager_type: The manager type to register.
        """
        if manager is not None:
            self.managers[name] = manager
        if manager_type is not None:
            self.manager_types[name] = manager_type

    def create_proxy(
        self,
        name=None,
        cls=None,
        args=(),
        kwargs=None,
        manager_type=None,
        manager=None,
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
        if cls is None:
            cls = self.proxy_type
        c_name = cls.__name__

        # Get Manager Type
        if manager_type is None:
            manager_type = self.manager_types.get(c_name, self.default_manager_type)
        elif c_name not in self.manager_types:
            self.manager_types[c_name] = manager_type

        if not hasattr(manager_type, c_name):
            manager_type.register(c_name, cls, exposed=exposed, **_kwargs)

        # Get Manager
        if manager is not None and c_name not in self.managers:
            self.managers[c_name] = manager
        elif (manager := self.managers.get(c_name, None)) is None:
            manager = manager_type()

        # Start the Manger and get the proxy
        if not manager.is_alive():
            proxy = manager.start_proxy(proxy_name=c_name, proxy_args=args, proxy_kwargs=kwargs)
        else:
            proxy = getattr(manager, c_name)(*args, **kwargs)

        # Register the Proxy
        p_ref = ref(proxy)
        p_name = name or str(id(proxy))
        self.proxy_register[p_name] = (p_ref, manager, manager_type)
        self.object_register["proxies"][p_name] = p_ref
        return proxy


# Assignment #
ManagerContext.contexts["multiprocessing"] = MultiProcessingContext()
