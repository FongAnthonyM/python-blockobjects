""" baseprocessingcontext.py
 multiprocessing object manager, managing the implementation, creation, and dispatch of multiprocessing objects.
"""
# Package Header #
from src.blockobjects.header import *

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
from baseobjects import BaseObject

# Local Packages #
from src.blockobjects.process.context.interfaces import LockInterface, EventInterface, QueueInterface, ProxyInterface


# Definitions #
# Classes #
class BaseProcessingContext(BaseObject):
    """A multiprocessing object manager, managing the implementation, creation, and dispatch of multiprocessing objects.

    Class Attributes:

    Attributes:
        object_categories: The names of the types of objects that will be managed this context.
        lock_type: The type of lock to create when creating locks.
        event_type: The type of event to create when creating events.
        queue_type: The type of queue to create when creating queues.
        simple_queue_type: The type of simple queue to create when creating simple queues.
        object_register: The multiprocessing objects managed by this context.

    Args:
        init: Determines if this object will construct.
    """
    # Class Attributes #

    # Attributes #
    object_categories: tuple[str] = ("locks", "events", "queues", "simple_queues", "proxies")
    lock_type: type[LockInterface] | None = None
    event_type: type[EventInterface] | None = None
    queue_type: type[QueueInterface] | None = None
    simple_queue_type: type[QueueInterface] | None = None
    proxy_type: type[ProxyInterface] | None = None
    object_register: dict[str, dict[str, Any]]

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, init: bool = True) -> None:
        # Attributes #
        self.object_register = {n: {} for n in self.object_categories}

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
        state = self.__dict__.copy()
        state["object_register"] = tuple(k for k in self.object_register.keys())
        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Builds this object based on a dictionary of corresponding attributes.

        Args:
            state: The attributes to build this object from.
        """
        object_categories = state.pop("object_register")
        self.__dict__.update(state)
        self.object_register = {n: {} for n in object_categories}

    # Instance Methods #
    # Constructors/Destructors
    def construct(self) -> None:
        super().construct()

    # Context Objects
    def create_lock(self, name=None, *args, cls=None, **kwargs) -> LockInterface:
        """Creates and adds a lock to the context's object register.

        Args:
            name: The name of the lock to create.
            *args: The arguments for creating the lock.
            cls: The class type of the lock to create.
            **kwargs: The keyword arguments for creating the lock.

        Returns:
            The lock.
        """
        if cls is None:
            cls = self.lock_type
        lock = cls(*args, **kwargs)
        self.object_register["locks"][(str(id(lock)) if name is None else name)] = ref(lock)
        return lock

    def require_lock(self, name, *args, cls=None, **kwargs) -> LockInterface:
        """Gets a lock if it exists otherwise it creates and adds a lock to the context's object register.

        Args:
            name: The name of the lock to require.
            *args: The arguments for creating the lock.
            cls: The class type of the lock to create.
            **kwargs: The keyword arguments for creating the lock.

        Returns:
            The lock.
        """
        if (lock := self.object_register["locks"].get(name, None)) is None:
            lock = self.create_lock(name, *args, cls=cls, **kwargs)
        return lock

    def register_lock(self, lock: LockInterface, name=None) -> None:
        """Adds a lock to the context's object register.

        Args:
            lock: The lock to add to the object contexts.
            name: The name of the lock.
        """
        self.object_register["locks"][(str(id(lock)) if name is None else name)] = ref(lock)

    def create_event(self, name=None, *args, cls=None, **kwargs) -> EventInterface:
        """Creates and adds an event to the context's object register.

        Args:
            name: The name of the event to create.
            *args: The arguments for creating the event.
            cls: The class type of the event to create.
            **kwargs: The keyword arguments for creating the event.

        Returns:
            The event.
        """
        if cls is None:
            cls = self.event_type
        event = cls(*args, **kwargs)
        self.object_register["events"][(str(id(event)) if name is None else name)] = ref(event)
        return event

    def require_event(self, name, *args, cls=None, **kwargs) -> EventInterface:
        """Gets an event if it exists otherwise it creates and adds an event to the context's object register.

        Args:
            name: The name of the event to require.
            *args: The arguments for creating the event.
            cls: The class type of the event to create.
            **kwargs: The keyword arguments for creating the event.

        Returns:
            The event.
        """
        if (event := self.object_register["events"].get(name, None)) is None:
            event = self.create_event(name, *args, cls=cls, **kwargs)
        return event

    def register_event(self, event: EventInterface, name=None) -> None:
        """Adds an event to the context's object register.

        Args:
            event: The event to add to the object register.
            name: The name of the event.
        """
        self.object_register["events"][(str(id(event)) if name is None else name)] = ref(event)

    def create_queue(self, name=None, *args, cls=None, **kwargs) -> QueueInterface:
        """Creates and adds a queue to the context's object register.

        Args:
            name: The name of the queue to create.
            *args: The arguments for creating the queue.
            cls: The class type of the queue to create.
            **kwargs: The keyword arguments for creating the queue.

        Returns:
            The queue.
        """
        if cls is None:
            cls = self.queue_type
        queue = cls(*args, **kwargs)
        self.object_register["queues"][(str(id(queue)) if name is None else name)] = ref(queue)
        return queue

    def require_queue(self, name, *args, cls=None, **kwargs) -> QueueInterface:
        """Gets a queue if it exists otherwise it creates and adds a queue to the context's object register.

        Args:
            name: The name of the queue to require.
            *args: The arguments for creating the queue.
            cls: The class type of the queue to create.
            **kwargs: The keyword arguments for creating the queue.

        Returns:
            The queue.
        """
        if (queue := self.object_register["queues"].get(name, None)) is None:
            queue = self.create_queue(name, *args, cls=cls, **kwargs)
        return queue

    def register_queue(self, queue: QueueInterface, name=None) -> None:
        """Adds a queue to the context's object register.

        Args:
            queue: The queue to add to the object register.
            name: The name of the queue.
        """
        self.object_register["queues"][(str(id(queue)) if name is None else name)] = ref(queue)

    def create_simple_queue(self, name=None, *args, cls=None, **kwargs) -> QueueInterface:
        """Creates and adds a simple queue to the context's object register.

        Args:
            name: The name of the simple queue to create.
            *args: The arguments for creating the simple queue.
            cls: The class type of the simple queue to create.
            **kwargs: The keyword arguments for creating the simple queue.

        Returns:
            The simple queue.
        """
        if cls is None:
            cls = self.simple_queue_type
        queue = cls(*args, **kwargs)
        self.object_register["simple_queues"][(str(id(queue)) if name is None else name)] = ref(queue)
        return queue

    def require_simple_queue(self, name, *args, cls=None, **kwargs) -> QueueInterface:
        """Gets a simple queue if it exists otherwise it creates and adds a simple queue to the context's object register.

        Args:
            name: The name of the queue to require.
            *args: The arguments for creating the queue.
            cls: The class type of the queue to create.
            **kwargs: The keyword arguments for creating the queue.

        Returns:
            The queue.
        """
        if (queue := self.object_register["simple_queues"].get(name, None)) is None:
            queue = self.create_simple_queue(name, *args, cls=cls, **kwargs)
        return queue

    def register_simple_queue(self, queue: QueueInterface, name=None) -> None:
        """Adds a simple queue to the context's object register.

        Args:
            queue: The simple queue to add to the object register.
            name: The name of the simple queue.
        """
        self.object_register["simple_queues"][(str(id(queue)) if name is None else name)] = ref(queue)

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
            *args: The arguments for creating the remote proxy.
            **kwargs: The keyword arguments for creating the remote proxy.

        Returns:
            The proxy.
        """
        if c_cls is None:
            c_cls = self.proxy_type

        proxy = c_cls.new_proxy(cls, args, kwargs=kwargs, *_args, exposed=exposed, **_kwargs)

        self.object_register["proxies"][(str(id(proxy)) if name is None else name)] = ref(proxy)
        return proxy

    def require_proxy(
        self,
        name=None,
        cls=None,
        args=(),
        kwargs=None,
        *_args,
        **_kwargs,
    ) -> ProxyInterface:
        """Gets a proxy if it exists otherwise it creates and adds a proxy to the context's object register.

        Args:
            name: The name of the remote proxy to create.
            cls: The class type of the remote proxy to create.
            args: The arguments for creating the remote proxy.
            kwargs: The keyword arguments for creating the remote proxy.

        Returns:
            The proxy.
        """
        if (proxy := self.object_register["proxies"].get(name, None)) is None:
            proxy = self.create_proxy(name, cls, args, kwargs, *_args, **_kwargs)
        return proxy

    def register_proxy(self, proxy: ProxyInterface, name=None) -> None:
        """Adds a proxy to the context's object register.

        Args:
            proxy: The proxy to add to the object register.
            name: The name of the proxy.
        """
        self.object_register["proxy"][(str(id(proxy)) if name is None else name)] = ref(proxy)
