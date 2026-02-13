"""contextuallock.py
An object that wraps a lock created by a context object and can switch between multiple contexts.

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
from contextlib import contextmanager
from typing import Any

# Third-Party Packages #

# Local Packages #
from ....interfaces import LockInterface
from ...bases import BaseProcessingContext, BaseContextualObject


# Definitions #
# Classes #
class ContextualLock(BaseContextualObject, LockInterface):
    """An object that wraps a lock created by a context object and can switch between multiple contexts.

    Attributes:
        lock: The lock to wrap.
    """

    # Attributes #
    lock: LockInterface | None = None

    # Instance Methods #
    # Constructors/Destructors
    def construct(self, *args: Any, context: BaseProcessingContext | None = None, **kwargs: Any) -> None:
        """Constructs this object.

        Args:
            context: The context of this Lock.
        """
        super().construct(*args, context=context, **kwargs)

        if self.context is not None:
            self.lock = self.context.require_lock(name=str(id(self)))

    # Context Managers
    def __enter__(self) -> "ContextualLock":
        """Enters the context by acquiring the lock."""
        self.acquire()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exits the context by releasing the lock."""
        self.release()

    # Context
    def set_context(self, context: BaseProcessingContext) -> None:
        """Sets the context of this object to the given context.

        Args:
            context: The context to assign this object to.
        """
        super().set_context(context=context)

        # Create a new lock ensuring the old lock it is acquired first.
        old_lock = self.lock
        old_lock.acquire()
        self.lock = context.require_lock(name=str(id(self)))
        old_lock.release()

    # Lock
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
        return self.lock.acquire(block=block, timeout=timeout)

    def release(self) -> None:
        """Releases the lock."""
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
        return await self.lock.acquire_async(block=block, timeout=timeout, interval=interval)

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
