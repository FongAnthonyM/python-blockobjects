""" contextuallock.py
Extends the multiprocessing Lock by adding async methods and interrupt for blocking methods.
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
from contextlib import contextmanager

# Third-Party Packages #

# Local Packages #
from ...baseprocesscontext import BaseProcessContext
from ...contextualobject import ContextualObject
from .lockinterface import LockInterface


# Definitions #
# Classes #
class ContextualLock(ContextualObject, LockInterface):
    """Extends the multiprocessing Lock by adding async methods and interrupt for blocking methods.

    Attributes:
        acquire_interrupt: An event which can be set to interrupt the acquire method blocking.

    Args:
        ctx: The context for the Python multiprocessing.
    """

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, *, context: BaseProcessContext | None = None, init: bool = True) -> None:
        # New Attributes #
        self.lock = None

        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct(context=context)

    # Instance Methods #
    # Context #
    def set_context(self, context: BaseProcessContext) -> None:
        super().set_context(context=context)
        old_lock = self.lock
        old_lock.aquire()
        self.lock = context.create_lock()
        old_lock.release()

    # Lock #
    def acquire(self, block: bool = True, timeout: float | None = None) -> bool:
        """Acquires the Lock, waits for the lock if block is True.

        Args:
            block: Determines if this method will block execution while waiting for the lock to be acquired.
            timeout: The time, in seconds, to wait for the lock to be acquired, otherwise returns False.

        Returns:
            If this method successful acquired or failed to a timeout.

        Raises:
            InterruptedError: When this method is interrupted by an interrupt event.
        """
        return self.lock.aquire(block=block, timeout=timeout)

    def release(self) -> None:
        self.lock.release()

    async def acquire_async(self, block: bool = True, timeout: float | None = None, interval: float = 0.0) -> bool:
        """Asynchronously acquires the Lock, waits for the lock if block is True.

        Args:
            block: Determines if this method will block execution while waiting for the lock to be acquired.
            timeout: The time, in seconds, to wait for the lock to be acquired, otherwise returns False.
            interval: The time, in seconds, between each set check.

        Returns:
            If this method successful acquired or failed to a timeout.

        Raises:
            InterruptedError: When this method is interrupted by an interrupt event.
        """
        return await self.lock.aquire_async(block=block, timeout=timeout, interval=interval)

    @contextmanager
    async def async_context(self, block: bool = True, timeout: float | None = None, interval: float = 0.0) -> "Lock":
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
