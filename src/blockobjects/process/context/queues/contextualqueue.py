""" contextualqueue.py
An object that wraps a queue created by a context object and can switch between multiple contexts.
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

# Third-Party Packages #

# Local Packages #
from src.blockobjects.process.context.bases.baseprocessingcontext import BaseProcessingContext
from ..contextualobject import BaseContextualObject
from ..interfaces import QueueInterface


# Definitions #
# Classes #
class ContextualQueue(BaseContextualObject, QueueInterface):
    """An object that wraps a queue created by a context object and can switch between multiple contexts.

    Attributes:
        queue: The queue to wrap.
        space_wait: Determines if this queue will wait for the queue space to enqueue an item.

    Args:
        maxsize: The maximum number items that can be in the queue.
        space_wait: Determines if this queue will wait for the queue space to enqueue an item.
        context: The context of this Queue.
        init: Determines if this object will construct.
    """
    # Attributes #
    queue: QueueInterface | None = None
    space_wait: bool

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        maxsize: int = 0,
        space_wait: bool = False,
        *,
        context: BaseProcessingContext | None = None,
        init: bool = True,
    ) -> None:
        # Attributes #
        self.space_wait: bool = space_wait

        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct(maxsize=maxsize, space_wait=space_wait, context=context)

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        maxsize: int = 0,
        space_wait: bool = False,
        *,
        context: BaseProcessingContext | None = None,
    ) -> None:
        """Constructs this object.

        Args:
            maxsize: The maximum number items that can be in the queue.
            space_wait: Determines if this queue will wait for the queue space to enqueue an item.
            context: The context of this Queue.
        """
        super().construct(context=context)

        if context is not None:
            self.queue = self.context.require_queue(name=str(id(self)), maxsize=maxsize, space_wait=space_wait)

    # Context
    def set_context(self, context: BaseProcessingContext) -> None:
        """Sets the context of this object to the given context.

        Args:
            context: The context to assign this object to.
        """
        super().set_context(context=context)

        # Create a new queue and move the contents to the new queue
        new_queue = context.require_queue(name=str(id(self)))
        while not self.queue.empty():
            new_queue.put(self.queue.get())
        self.queue = new_queue

    # Queue
    def get(self, block: bool = True, timeout: float | None = None) -> Any:
        """Gets an item from the queue, waits for an item if the queue is empty.

        Args:
            block: Determines if this method will block execution.
            timeout: The time, in seconds, to wait for an item in the queue.

        Returns:
            The requested item.

        Raises:
            Empty: When there are no items to get in the queue when not blocking or on timing out.
            InterruptedError: When this method is interrupted by the interrupt event.
        """
        return self.queue.get(block=block, timeout=timeout)

    async def get_async(self, block: bool = True, timeout: float | None = None, interval: float = 0.0) -> Any:
        """Asynchronously gets an item from the queue, waits for an item if the queue is empty.

        Args:
            block: Determines if this method will block execution.
            timeout: The time, in seconds, to wait for an item in the queue.
            interval: The time, in seconds, between each queue check.

        Returns:
            The requested item.

        Raises:
            Empty: When there are no items to get in the queue when not blocking or on timing out.
            InterruptedError: When this method is interrupted by the interrupt event.
        """
        return await self.queue.get(block=block, timeout=timeout, interval=interval)

    def put(self, obj: Any, block: bool = True, timeout: float | None = None) -> None:
        """Puts an object into the queue, waits for access to the queue.

        Args:
            obj: The object to put into the queue.
            block: Determines if this method will block execution.
            timeout: The time, in seconds, to wait for space in the queue.

        Raises:
            Full: When there is no more space to put an item in the queue when not blocking or on timing out.
            InterruptedError: When this method is interrupted by the interrupt event.
        """
        return self.queue.put(obj=obj, block=block, timeout=timeout)

    async def put_async(self, obj: Any, timeout: float | None = None, interval: float = 0.0) -> None:
        """Asynchronously puts an object into the queue, waits for access to the queue.

        Args:
            obj: The object to put into the queue.
            timeout: The time, in seconds, to wait for space in the queue.
            interval: The time, in seconds, between each access check.

        Raises:
            Full: When there is no more space to put an item in the queue when not blocking or on timing out.
            InterruptedError: When this method is interrupted by the interrupt event.
        """
        return await self.queue.put_async(obj=obj, timeout=timeout, interval=interval)

    def join(self) -> None:
        """Blocks until all items in the Queue have been gotten and the registry is updated."""
        self.queue.join()

    async def join_async(self, interval: float = 0.0) -> None:
        """Asynchronously, blocks until all items in the Queue have been gotten and the registry is updated.

        Args:
            interval: The time, in seconds, between each queue check.
        """
        await self.queue.join_async(interval=interval)
