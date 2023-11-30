""" processcontext.py.py

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

# Local Packages #
from .baseprocesscontext import BaseProcessContext
from .synchronize import LockInterface, EventInterface
from .synchronize import ContextualEvent, ContextualLock
from .queues import QueueInterface
from .queues import ContextualQueue, ContextualSimpleQueue


# Definitions #
# Classes #
class ProcessContext(BaseProcessContext):
    """

    Class Attributes:

    Attributes:

    Args:

    """
    register: dict[str, BaseProcessContext] = {}
    lock_type: type[ContextualLock] = ContextualLock
    event_type: type[ContextualEvent] = ContextualEvent
    queue_type: type[ContextualQueue] = ContextualQueue
    simple_queue_type: type[ContextualSimpleQueue] = ContextualSimpleQueue

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, context, init: bool = True) -> None:
        # New Attributes #
        self.context: BaseProcessContext | None = None
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

    def set_context(self, name):
        self.context = self.register[name]

    def set_all_object_context(self, context):
        for obj_category in self.objects.values():
            empty_names = []
            for name, obj_ in obj_category.items():
                if (object_ := obj_()) is not None:
                    object_.set_context(context)
                else:
                    empty_names.append(name)
            for name in empty_names:
                del obj_category[name]

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
        return super().create_lock(name, *args, cls=cls, context=self.context, **kwargs)

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
        return super().create_event(name, *args, cls=cls, context=self.context, **kwargs)

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
        return super().create_queue(name, *args, cls=cls, context=self.context, **kwargs)

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
        return super().create_simple_queue(name, *args, cls=cls, context=self.context, **kwargs)


# Constants #
DEFAULT_PROCESS_CONTEXT = ProcessContext()
