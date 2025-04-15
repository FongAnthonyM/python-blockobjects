""" contextualqueue.py
An object that wraps a queue created by a context object and can switch between multiple context.
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
from baseobjects import search_sentinel

# Local Packages #
from ....interfaces import QueueInterface
from ...bases import BaseProcessingContext, BaseContextualObject


# Definitions #
# Classes #
class ContextualQueue(BaseContextualObject, QueueInterface):
    """An object that wraps a queue created by a context object and can switch between multiple context.

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
    space_wait: bool = False

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        maxsize: int = 0,
        space_wait: bool = True,
        *,
        context: BaseProcessingContext | None = None,
        init: bool = True,
    ) -> None:
        # Attributes #

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
        space_wait: bool = True,
        *,
        context: BaseProcessingContext | None = None,
    ) -> None:
        """Constructs this object.

        Args:
            maxsize: The maximum number items that can be in the queue.
            space_wait: Determines if this queue will wait for the queue space to enqueue an item.
            context: The context of this Queue.
        """
        if space_wait is not None:
            self.space_wait = space_wait

        super().construct(context=context)

        if self.context is not None:
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
    # State
    def empty(self) -> bool:
        """Returns True if the queue is empty, False otherwise."""
        return self.queue.empty()

    def poll(self) -> bool:
        """Returns True if the queue has something in it, False otherwise."""
        return self.queue.poll()

    # Size
    def set_maxsize(self, maxsize: int) -> None:
        """Sets the maximum size allowed for the queue.

        This method sets the maximum size of the queue by invoking the underlying set_maxsize method. This value
        determines the total number of elements the queue can hold.

        Args:
            maxsize: The maximum size to set for the queue.
        """
        self.queue.set_maxsize(maxsize)

    def get_maxsize(self) -> int:
        """Gets the maximum size of the queue.

        This method returns the maximum number of items that the queue can hold. It is useful for determining
        capacity constraints of the queue in a specific scenario.

        Returns:
            int: The maximum size of the queue.
        """
        return self.queue.get_maxsize()

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
    def join(self, *args: Any, **kwargs: Any) -> None:
        """Blocks until all items in the Queue have been gotten and the registry is updated."""
        self.queue.join(*args, **kwargs)

    async def join_async(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously, blocks until all items in the Queue have been gotten and the registry is updated."""
        await self.queue.join_async(*args, **kwargs)
