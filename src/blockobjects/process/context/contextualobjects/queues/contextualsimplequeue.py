""" contextualsimplequeue.py
An object that wraps a simple queue created by a context object and can switch between multiple context.
"""
# Package Header #
from .....header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Standard Libraries #
from typing import Any

# Third-Party Packages #
from baseobjects import search_sentinel

# Local Packages #
from ....interfaces import QueueInterface
from ...bases import BaseProcessingContext, BaseContextualObject


# Definitions #
# Classes #
class ContextualSimpleQueue(BaseContextualObject, QueueInterface):
    """An object that wraps a simple queue created by a context object and can switch between multiple context.

    Attributes:
        queue: The simple queue to wrap.
    """
    # Attributes #
    queue: QueueInterface | None = None

    # Instance Methods #
    # Constructors/Destructors
    def construct(self, *args: Any, context: BaseProcessingContext | None = None, **kwargs: Any) -> None:
        """Constructs this object.

        Args:
            context: The context of this Queue.
        """
        super().construct(*args, context=context, **kwargs)

        if self.context is not None:
            self.queue = self.context.require_simple_queue(name=str(id(self)))

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
    # State
    def empty(self) -> bool:
        """Returns True if the queue is empty, False otherwise."""
        return self.queue.empty()

    def poll(self) -> bool:
        """Returns True if the queue has something in it, False otherwise."""
        return self.queue.poll()

    # Get
    def get(
        self,
        block: bool = True,
        timeout: float | None = None,
        default: Any = search_sentinel,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
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
        return self.queue.get(block=block, timeout=timeout, default=default, *args, **kwargs)

    async def get_async(
        self,
        block: bool = True,
        timeout: float | None = None,
        interval: float = 0.0,
        default: Any = search_sentinel,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
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
        return await self.queue.get_async(
            block=block,
            timeout=timeout,
            interval=interval,
            default=default,
            *args,
            **kwargs,
        )

    # Put
    def put(self, value: Any, block: bool = True, timeout: float | None = None, *args: Any, **kwargs: Any) -> None:
        """Puts a value into the queue, waits for access to the queue.

        Args:
            value: The value to put into the queue.
            block: Determines if this method will block execution.
            timeout: The time, in seconds, to wait for space in the queue.

        Raises:
            Full: When there is no more space to put an item in the queue when not blocking or on timing out.
            InterruptedError: When this method is interrupted by the interrupt event.
        """
        return self.queue.put(value=value, block=block, timeout=timeout)

    async def put_async(
        self,
        value: Any,
        timeout: float | None = None,
        interval: float = 0.0,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Asynchronously puts a value into the queue, waits for access to the queue.

        Args:
            value: The value to put into the queue.
            timeout: The time, in seconds, to wait for space in the queue.
            interval: The time, in seconds, between each access check.

        Raises:
            Full: When there is no more space to put an item in the queue when not blocking or on timing out.
            InterruptedError: When this method is interrupted by the interrupt event.
        """
        return await self.queue.put_async(value=value, timeout=timeout, interval=interval)

    # Join
    def join(self) -> None:
        """Blocks until all items in the Queue have been gotten and the registry is updated."""
        self.queue.join()

    async def join_async(self) -> None:
        """Asynchronously, blockgroup until all items in the Queue have been gotten and the registry is updated."""
        await self.queue.join_async()
