""" baseprocesscontext.py

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


# Definitions #
# Classes #
class BaseProcessContext(BaseObject):
    """

    Class Attributes:

    Attributes:

    Args:

    """
    lock_type: type[LockInterface] | None = None
    event_type: type[EventInterface] | None = None
    queue_type: type[QueueInterface] | None = None
    simple_queue_type: type[QueueInterface] | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, context, init: bool = True) -> None:
        # New Attributes #
        self.objects: dict[str, dict[str, Any]] = {}

        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct(context=context)

    # Instance Methods #
    # Constructors/Destructors
    def construct(self, context) -> None:
        super().construct()

    # Context Objects
    def create_lock(self, name=None, *args, cls=None, **kwargs) -> LockInterface:
        """Creates and adds a lock to the context's register.

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

    def register_lock(self, lock: LockInterface, name=None) -> None:
        """Adds a lock to the context's object register.

        Args:
            lock: The lock to add to the object register.
            name: The name of the lock.
        """
        self.objects["locks"][(str(id(lock)) if name is None else name)] = ref(lock)

    def create_event(self, name=None, *args, cls=None, **kwargs) -> EventInterface:
        """Creates and adds an event to the context's register.

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

    def register_event(self, event: EventInterface, name=None) -> None:
        """Adds an event to the context's object register.

        Args:
            event: The event to add to the object register.
            name: The name of the event.
        """
        self.objects["events"][(str(id(event)) if name is None else name)] = ref(event)

    def create_queue(self, name=None, *args, cls=None, **kwargs) -> QueueInterface:
        """Creates and adds a queue to the context's register.

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

    def register_queue(self, queue: QueueInterface, name=None) -> None:
        """Adds a queue to the context's object register.

        Args:
            queue: The queue to add to the object register.
            name: The name of the queue.
        """
        self.objects["queues"][(str(id(queue)) if name is None else name)] = ref(queue)

    def create_simple_queue(self, name=None, *args, cls=None, **kwargs) -> QueueInterface:
        """Creates and adds a simple queue to the context's register.

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

    def register_simple_queue(self, queue: QueueInterface, name=None) -> None:
        """Adds a simple queue to the context's object register.

        Args:
            queue: The simple queue to add to the object register.
            name: The name of the simple queue.
        """
        self.objects["simple_queues"][(str(id(queue)) if name is None else name)] = ref(queue)
