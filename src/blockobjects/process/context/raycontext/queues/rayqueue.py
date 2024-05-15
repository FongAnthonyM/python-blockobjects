""" rayqueue.py
Extends the multiprocessing Queue by adding async methods and interrupts for blocking methods.
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
from types import GenericAlias

# Third-Party Packages #
from baseobjects import search_sentinel
from ray import remote, get
from ray.actor import ActorClass, ActorHandle

# Local Packages #
from ....interfaces import QueueInterface
from ...asynccontext import AsyncQueue


# Definitions #
# Classes #
class _AsyncQueue(AsyncQueue):

    # Class Magic Methods #
    def __class_getitem__(cls, item: Any) -> GenericAlias:
        """Overrides previous implementation to allow signature inspection of this method."""
        return GenericAlias(cls, item)


class RayQueue(QueueInterface):
    """Extends the multiprocessing Queue by adding async methods and interrupts for blocking methods.

    Class Attributes:
        _ignore_attributes: The attributes to not pickle when pickling.

    Attributes:
        space_wait: Determines if this queue will wait for the queue space to enqueue an item.

    Args:
        maxsize: The maximum number items that can be in the queue.
        space_wait: Determines if this queue will wait for the queue space to enqueue an item.
        ctx: The context for the Python multiprocessing.
    """
    # Attributes #
    _remote_queue_class: ActorClass = remote(num_cpus=0)(_AsyncQueue)
    _remote_queue: ActorHandle | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, maxsize: int = 0, *args: Any, **kwargs: Any) -> None:
        # Attributes #
        self._remote_queue = self._remote_queue_class.remote(maxsize=maxsize)

        # Construction #
        super().__init__(*args, **kwargs)

    # Instance Methods #
    # State
    def qsize(self) -> int:
        """Number of items in the queue."""
        return get(self._remote_queue.qsize.remote())

    def poll(self) -> bool:
        """Returns True if the queue has something in it, False otherwise."""
        return get(self._remote_queue.poll.remote())

    def empty(self) -> bool:
        """Return True if the queue is empty, False otherwise."""
        return get(self._remote_queue.empty.remote())

    def full(self) -> bool:
        """Return True if there are maxsize items in the queue.

        Note: if the Queue was initialized with maxsize=0 (the default),
        then full() is never True.
        """
        return get(self._remote_queue.full.remote())

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
        # Run the async get to not block the remote actor
        return get(self._remote_queue.get_async.remote(block, timeout, default, *args, **kwargs))

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
        return await self._remote_queue.get_async.remote(block, timeout, interval, default, *args, **kwargs)

    def get_nowait(self) -> Any:
        """Remove and return an item from the queue.

        Return an item if one is immediately available, else raise QueueEmpty.
        """
        get(self._remote_queue.get_nowait.remote())

    # Put
    def put(
        self,
        value: Any,
        block: bool = True,
        timeout: float | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Puts a value into the queue, waits for access to the queue.

        Args:
            value: The value to put into the queue.
            block: Determines if this method will block execution.
            timeout: The time, in seconds, to wait for space in the queue.

        Raises:
            Full: When there is no more space to put an item in the queue when not blocking or on timing out.
            InterruptedError: When this method is interrupted by the interrupt event.
        """
        self._remote_queue.put_async.remote(value, block, timeout, *args, **kwargs)

    async def put_async(
        self,
        value: Any,
        block: bool = True,
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
        await self._remote_queue.put_async.remote(value, block, timeout, *args, **kwargs)

    def put_nowait(self, value: Any) -> None:
        """Equivalent to put(item, block=False).

        Raises:
            Full: if the queue is full.
        """
        self._remote_queue.put_nowait.remote(value)

    def task_done(self) -> None:
        """Indicate that a formerly enqueued task is complete.

        Used by queue consumers. For each get() used to fetch a task,
        a subsequent call to task_done() tells the queue that the processing
        on the task is complete.

        If a join() is currently blocking, it will resume when all items have
        been processed (meaning that a task_done() call was received for every
        item that had been put() into the queue).

        Raises ValueError if called more times than there were items placed in
        the queue.
        """
        self._remote_queue.task_done.remote()

    # Join
    def join(self) -> None:
        """Blocks until all items in the Queue have been gotten and the registry is updated."""
        get(self._remote_queue.join_async.remote())

    async def join_async(self, interval: float = 0.0) -> None:
        """Asynchronously, blocks until all items in the Queue have been gotten and the registry is updated.

        Args:
            interval: The time, in seconds, between each queue check.
        """
        await self._remote_queue.join_async.remote()
