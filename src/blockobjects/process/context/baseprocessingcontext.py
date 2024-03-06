""" baseprocessingcontext.py
 multiprocessing object manager, managing the implementation, creation, and dispatch of multiprocessing objects.
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
from typing import Any
from weakref import ref

# Third-Party Packages #
from baseobjects import BaseObject

# Local Packages #
from .synchronize import LockInterface, EventInterface
from .queues import QueueInterface
from .proxies import ProxyInterface


# Definitions #
# Classes #
class BaseProcessingContext(BaseObject):
    """A multiprocessing object manager, managing the implementation, creation, and dispatch of multiprocessing objects.

    Class Attributes:

    Attributes:
        object_categories: The names of the types of objects that will be created by this context.
        lock_type: The type of lock to create when creating locks.
        event_type: The type of event to create when creating events.
        queue_type: The type of queue to create when creating queues.
        simple_queue_type: The type of simple queue to create when creating simple queues.
        objects: The multiprocessing objects managed by this context.

    Args:
        init: Determines if this object will construct.
    """
    # Class Attributes #

    # Attributes #
    object_categories: tuple[str] = ("locks", "events", "queues", "simple_queues", "remote_executors")
    lock_type: type[LockInterface] | None = None
    event_type: type[EventInterface] | None = None
    queue_type: type[QueueInterface] | None = None
    simple_queue_type: type[QueueInterface] | None = None
    proxy_type: type[ProxyInterface] | None = None
    objects: dict[str, dict[str, Any]]

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, init: bool = True) -> None:
        # Attributes #
        self.objects: dict[str, dict[str, Any]] = {n: {} for n in self.object_categories}

        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct()

    # Instance Methods #
    # Constructors/Destructors
    def construct(self) -> None:
        super().construct()

    # Context Objects
    def create_lock(self, name=None, *args, cls=None, **kwargs) -> LockInterface:
        """Creates and adds a lock to the context's contexts.

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
        self.objects["locks"][(str(id(lock)) if name is None else name)] = ref(lock)
        return lock

    def require_lock(self, name, *args, cls=None, **kwargs) -> LockInterface:
        """Gets a lock if it exists otherwise it creates and adds a lock to the context's contexts.

        Args:
            name: The name of the lock to require.
            *args: The arguments for creating the lock.
            cls: The class type of the lock to create.
            **kwargs: The keyword arguments for creating the lock.

        Returns:
            The lock.
        """
        if (lock := self.objects["locks"].get(name, None)) is None:
            lock = self.create_lock(name, *args, cls=cls, **kwargs)
        return lock

    def register_lock(self, lock: LockInterface, name=None) -> None:
        """Adds a lock to the context's object contexts.

        Args:
            lock: The lock to add to the object contexts.
            name: The name of the lock.
        """
        self.objects["locks"][(str(id(lock)) if name is None else name)] = ref(lock)

    def create_event(self, name=None, *args, cls=None, **kwargs) -> EventInterface:
        """Creates and adds an event to the context's contexts.

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
        self.objects["events"][(str(id(event)) if name is None else name)] = ref(event)
        return event

    def require_event(self, name, *args, cls=None, **kwargs) -> EventInterface:
        """Gets an event if it exists otherwise it creates and adds an event to the context's contexts.

        Args:
            name: The name of the event to require.
            *args: The arguments for creating the event.
            cls: The class type of the event to create.
            **kwargs: The keyword arguments for creating the event.

        Returns:
            The event.
        """
        if (event := self.objects["events"].get(name, None)) is None:
            event = self.create_event(name, *args, cls=cls, **kwargs)
        return event

    def register_event(self, event: EventInterface, name=None) -> None:
        """Adds an event to the context's object contexts.

        Args:
            event: The event to add to the object contexts.
            name: The name of the event.
        """
        self.objects["events"][(str(id(event)) if name is None else name)] = ref(event)

    def create_queue(self, name=None, *args, cls=None, **kwargs) -> QueueInterface:
        """Creates and adds a queue to the context's contexts.

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
        self.objects["queues"][(str(id(queue)) if name is None else name)] = ref(queue)
        return queue

    def require_queue(self, name, *args, cls=None, **kwargs) -> QueueInterface:
        """Gets a queue if it exists otherwise it creates and adds a queue to the context's contexts.

        Args:
            name: The name of the queue to require.
            *args: The arguments for creating the queue.
            cls: The class type of the queue to create.
            **kwargs: The keyword arguments for creating the queue.

        Returns:
            The queue.
        """
        if (queue := self.objects["queues"].get(name, None)) is None:
            queue = self.create_queue(name, *args, cls=cls, **kwargs)
        return queue

    def register_queue(self, queue: QueueInterface, name=None) -> None:
        """Adds a queue to the context's object contexts.

        Args:
            queue: The queue to add to the object contexts.
            name: The name of the queue.
        """
        self.objects["queues"][(str(id(queue)) if name is None else name)] = ref(queue)

    def create_simple_queue(self, name=None, *args, cls=None, **kwargs) -> QueueInterface:
        """Creates and adds a simple queue to the context's contexts.

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
        self.objects["simple_queues"][(str(id(queue)) if name is None else name)] = ref(queue)
        return queue

    def require_simple_queue(self, name, *args, cls=None, **kwargs) -> QueueInterface:
        """Gets a simple queue if it exists otherwise it creates and adds a simple queue to the context's contexts.

        Args:
            name: The name of the queue to require.
            *args: The arguments for creating the queue.
            cls: The class type of the queue to create.
            **kwargs: The keyword arguments for creating the queue.

        Returns:
            The queue.
        """
        if (queue := self.objects["simple_queues"].get(name, None)) is None:
            queue = self.create_simple_queue(name, *args, cls=cls, **kwargs)
        return queue

    def register_simple_queue(self, queue: QueueInterface, name=None) -> None:
        """Adds a simple queue to the context's object contexts.

        Args:
            queue: The simple queue to add to the object contexts.
            name: The name of the simple queue.
        """
        self.objects["simple_queues"][(str(id(queue)) if name is None else name)] = ref(queue)

    def create_proxy(self, name=None, *args, cls=None, **kwargs) -> ProxyInterface:
        """Creates and adds a remote executor to the context's contexts.

        Args:
            name: The name of the remote executor to create.
            *args: The arguments for creating the remote executor.
            cls: The class type of the remote executor to create.
            **kwargs: The keyword arguments for creating the remote executor.

        Returns:
            The remote executor.
        """
        if cls is None:
            cls = self.proxy_type
        executor = cls(*args, **kwargs)
        self.objects["locks"][(str(id(executor)) if name is None else name)] = ref(executor)
        return executor

    def require_proxy(self, name, *args, cls=None, **kwargs) -> ProxyInterface:
        """Gets an executor if it exists otherwise it creates and adds a remote executor to the context's contexts.

        Args:
            name: The name of the remote executor to require.
            *args: The arguments for creating the remote executor.
            cls: The class type of the remote executor to create.
            **kwargs: The keyword arguments for creating the remote executor.

        Returns:
            The remote executor.
        """
        if (executor := self.objects["remote_executors"].get(name, None)) is None:
            executor = self.create_proxy(name, *args, cls=cls, **kwargs)
        return executor
