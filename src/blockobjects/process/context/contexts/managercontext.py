""" managercontext.py.py
A context which manages multiple contexts and delegates its context functionality to a selected context.
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

# Third-Party Packages #

# Local Packages #
from ..bases import BaseProcessingContext
from ..interfaces import LockInterface, EventInterface, QueueInterface, ProxyInterface
from ..synchronize import ContextualLock, ContextualEvent
from ..queues import ContextualQueue, ContextualSimpleQueue
from ..proxies import ContextualProxy


# Definitions #
# Classes #
class ManagerContext(BaseProcessingContext):
    """A context which manages multiple contexts and delegates its context functionality to a selected context.

    Attributes:
        lock_type: The type of lock to create when creating locks.
        event_type: The type of event to create when creating events.
        queue_type: The type of queue to create when creating queues.
        simple_queue_type: The type of simple queue to create when creating simple queues.

        contexts: The process contexts to manage.
        context: The selected context to delegate functionality to.
        selected: The key name of the context to delegate functionality to.

    Args:
        contexts: The process contexts to manage.
        select: The key name of the context which this manager context will delegate to.
        init: Determines if this object will construct.
    """
    # Attributes  #
    lock_type: type[ContextualLock] = ContextualLock
    event_type: type[ContextualEvent] = ContextualEvent
    queue_type: type[ContextualQueue] = ContextualQueue
    simple_queue_type: type[ContextualSimpleQueue] = ContextualSimpleQueue
    proxy_type: type[ContextualProxy] = ContextualProxy

    contexts: dict[str, BaseProcessingContext] = {}
    context: BaseProcessingContext | None = None
    selected: str | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        contexts: dict[str, BaseProcessingContext] | None = None,
        select: str | None = None,
        init: bool = True,
    ) -> None:
        # New Attributes #
        self.contexts = self.contexts.copy()

        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct(contexts=contexts, select=select)

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        contexts: dict[str, BaseProcessingContext] | None = None,
        select: str | None = None,
    ) -> None:
        """Constructs this object.

        Args:
            contexts: The process contexts to manage.
            select: The key name of the context which this manager context will delegate to.
        """
        if contexts is not None:
            self.contexts.update(contexts)

        if select is not None:
            self.select_context(select)

        super().construct()

    # Context Management
    def select_context(self, name: str, update: bool = False) -> None:
        """Selects a contained context as the context which this manager context will delegate to.

        Args:
            name: The key name of the context which this manager context will delegate to.
            update: Determines whether the contained objects will change to the new context. Defaults to False
        """
        self.context = self.contexts[name]
        self.selected = name

        if update:
            self.set_all_objects_context(self.context)

    def set_all_objects_context(self, context: BaseProcessingContext) -> None:
        """Sets all contained objects to a given context.

        Args:
            context: The context to set the objects to.
        """
        for obj_category in self.objects.values():
            empty_names = []
            for name, obj_ in obj_category.items():
                if (object_ := obj_()) is not None:
                    object_.set_context(context)
                else:
                    empty_names.append(name)
            for name in empty_names:
                del obj_category[name]

    def set_all_objects_to_selected_context(self) -> None:
        """Sets all contained objects to the selected context."""
        self.set_all_objects_context(context=self.context)

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
        return super().create_lock(name, *args, cls=cls, **({"context": self.context} | kwargs))

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
        return super().create_event(name, *args, cls=cls, **({"context": self.context} | kwargs))

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
        return super().create_queue(name, *args, cls=cls, **({"context": self.context} | kwargs))

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
        return super().create_simple_queue(name, *args, cls=cls, **({"context": self.context} | kwargs))

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
        return super().create_proxy(
            name,
            cls,
            args,
            kwargs,
            *_args,
            c_cls=c_cls,
            exposed=exposed,
            **({"context": self.context} | _kwargs),
        )

