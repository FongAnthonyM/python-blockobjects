""" asynclock.py
A Lock object using Async.
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
from asyncio import Lock, wait_for, CancelledError
from collections import deque
from contextlib import contextmanager
from time import perf_counter

# Third-Party Packages #

# Local Packages #
from ....interfaces import LockInterface


# Definitions #
# Classes #
class AsyncLock(Lock, LockInterface):
    # Magic Methods #
    # Context Manager
    def __enter__(self):
        self.acquire()
        return None

    def __exit__(self, exc_type, exc, tb):
        self.release()

    async def __aenter__(self):
        await self.acquire_async()
        return None

    # Instance Methods #
    def acquire(self, block: bool = True, timeout: float | None = None) -> bool:
        """Acquires the Lock, waits for the lock if block is True.

        Args:
            block: Determines if this method will block execution while waiting for the lock to be acquired.
            timeout: The time, in seconds, to wait for the lock to be acquired, otherwise returns False.

        Returns:
            If this method successful acquired or failed to a timeout.
        """
        if not self._locked and (self._waiters is None or all(w.cancelled() for w in self._waiters)):
            self._locked = True
            return True
        elif not block:
            return False

        if self._waiters is None:
            self._waiters = deque()
        fut = self._get_loop().create_future()
        self._waiters.append(fut)

        try:
            if timeout is None:
                while True:
                    if fut.done():
                        self._locked = True
                        return True
            else:
                deadline = perf_counter() + timeout
                while True:
                    if fut.done():
                        self._locked = True
                        return True
                    if deadline <= perf_counter():
                        return False
        except CancelledError:
            if not self._locked:
                self._wake_up_first()
            raise

    async def acquire_async(self, block: bool = True, timeout: float | None = None, interval: float = 0.0) -> bool:
        """Asynchronously acquires the Lock, waits for the lock if block is True.

        Args:
            block: Determines if this method will block execution while waiting for the lock to be acquired.
            timeout: The time, in seconds, to wait for the lock to be acquired, otherwise returns False.
            interval: The time, in seconds, between each set check.

        Returns:
            If this method successful acquired or failed to a timeout.
        """
        if not self._locked and (self._waiters is None or all(w.cancelled() for w in self._waiters)):
            self._locked = True
            return True
        elif not block:
            return False

        if self._waiters is None:
            self._waiters = deque()
        fut = self._get_loop().create_future()
        self._waiters.append(fut)

        try:
            try:
                await wait_for(fut, timeout)
            finally:
                self._waiters.remove(fut)
        except CancelledError:
            if not self._locked:
                self._wake_up_first()
            raise

    @contextmanager
    async def async_context(
        self,
        block: bool = True,
        timeout: float | None = None,
        interval: float = 0.0,
    ) -> "AsyncLock":
        """Asynchronous context manager for acquiring and releasing the Lock.

        Args:
            block: Determines if this method will block execution while waiting for the lock to be acquired.
            timeout: The time, in seconds, to wait for the lock to be acquired, otherwise returns False.
            interval: The time, in seconds, between each set check.

        Returns:
            This Lock object.
        """
        try:
            await self.acquire_async(block=block, timeout=timeout, interval=interval)
            yield self
        finally:
            self.release()
