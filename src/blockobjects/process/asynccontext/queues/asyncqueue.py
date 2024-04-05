""" asyncqueue.py
Extends the multiprocessing Queue by adding async methods and interrupts for blocking methods.
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
from asyncio import sleep, Queue, wait_for, QueueFull, QueueEmpty, TimeoutError
from time import perf_counter
from typing import Any
from types import GenericAlias

# Third-Party Packages #
from baseobjects import search_sentinel

# Local Packages #
from ...context import QueueInterface


# Definitions #
# Classes #
class AsyncQueue(Queue, QueueInterface):

    # Attributes #
    tracking: bool = False

    # Instance Methods #
    # State
    def poll(self) -> bool:
        """Returns True if the queue has something in it, False otherwise."""
        return bool(self._queue)

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
        if block:
            while self.empty():
                getter = self._get_loop().create_future()
                self._getters.append(getter)
                try:
                    if timeout is None:
                        while not getter.done():
                            pass
                    else:
                        deadline = perf_counter() + timeout
                        while not getter.done():
                            if deadline is not None and deadline <= perf_counter():
                                if default is search_sentinel:
                                    raise TimeoutError
                                else:
                                    return default
                except:
                    getter.cancel()  # Just in case getter is not done yet.
                    try:
                        # Clean self._getters from canceled getters.
                        self._getters.remove(getter)
                    except ValueError:
                        # The getter could be removed from self._getters by a
                        # previous put_nowait call.
                        pass
                    if not self.empty() and not getter.cancelled():
                        # We were woken up by put_nowait(), but can't take
                        # the call.  Wake up the next in line.
                        self._wakeup_next(self._getters)
                    raise

        if self.empty():
            if default is search_sentinel:
                raise QueueEmpty
            else:
                return default
        item = self._get()
        self._wakeup_next(self._putters)
        return item

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
        """
        if block:
            while self.empty():
                getter = self._get_loop().create_future()
                self._getters.append(getter)
                try:
                    await wait_for(getter, timeout)
                except:
                    getter.cancel()  # Just in case getter is not done yet.
                    try:
                        # Clean self._getters from canceled getters.
                        self._getters.remove(getter)
                    except ValueError:
                        # The getter could be removed from self._getters by a
                        # previous put_nowait call.
                        pass
                    if not self.empty() and not getter.cancelled():
                        # We were woken up by put_nowait(), but can't take
                        # the call.  Wake up the next in line.
                        self._wakeup_next(self._getters)
                    elif default is not search_sentinel:
                        return search_sentinel
                    raise

        if self.empty():
            if default is search_sentinel:
                raise QueueEmpty
            else:
                return default
        item = self._get()
        self._wakeup_next(self._putters)
        return item

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
        """
        if block:
            while self.full():
                putter = self._get_loop().create_future()
                self._putters.append(putter)
                try:
                    if timeout is None:
                        while not putter.done():
                            pass
                    else:
                        deadline = perf_counter() + timeout
                        while not putter.done():
                            if deadline is not None and deadline <= perf_counter():
                                raise QueueFull
                except:
                    putter.cancel()  # Just in case putter is not done yet.
                    try:
                        # Clean self._putters from canceled putters.
                        self._putters.remove(putter)
                    except ValueError:
                        # The putter could be removed from self._putters by a
                        # previous get_nowait call.
                        pass
                    if not self.full() and not putter.cancelled():
                        # We were woken up by get_nowait(), but can't take
                        # the call.  Wake up the next in line.
                        self._wakeup_next(self._putters)
                    raise

        if self.full():
            raise QueueFull
        self._put(value)
        self._unfinished_tasks += 1 if self.tracking else 0
        self._finished.clear()
        self._wakeup_next(self._getters)

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
            block: Determines if this method will block execution.
            timeout: The time, in seconds, to wait for space in the queue.
            interval: The time, in seconds, between each access check.

        Raises:
            Full: When there is no more space to put an item in the queue when not blocking or on timing out.
        """
        if block:
            while self.full():
                putter = self._get_loop().create_future()
                self._putters.append(putter)
                try:
                    await wait_for(putter, timeout)
                except:
                    putter.cancel()  # Just in case putter is not done yet.
                    try:
                        # Clean self._putters from canceled putters.
                        self._putters.remove(putter)
                    except ValueError:
                        # The putter could be removed from self._putters by a
                        # previous get_nowait call.
                        pass
                    if not self.full() and not putter.cancelled():
                        # We were woken up by get_nowait(), but can't take
                        # the call.  Wake up the next in line.
                        self._wakeup_next(self._putters)
                    raise

        self._put(value)
        self._unfinished_tasks += 1 if self.tracking else 0
        self._finished.clear()
        self._wakeup_next(self._getters)

    def put_nowait(self, item) -> None:
        """Put an item into the queue without blocking.

        If no free slot is immediately available, raise QueueFull.
        """
        if self.full():
            raise QueueFull
        self._put(item)
        self._unfinished_tasks += 1 if self.tracking else 0
        self._finished.clear()
        self._wakeup_next(self._getters)

    # Join
    def join(self) -> None:
        """Blocks until all items in the Queue have been gotten and the registry is updated."""
        if self.tracking:
            while self._unfinished_tasks > 0:
                pass
        else:
            while not self.empty():
                pass

    async def join_async(self, interval: float = 0.0) -> None:
        if self.tracking:
            if self._unfinished_tasks > 0:
                await self._finished.wait()
        else:
            while self.qsize() > 0:
                await sleep(interval)
