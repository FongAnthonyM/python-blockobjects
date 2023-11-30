""" lockinterface.py
An interface which outlines the basis for a lock.
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
from abc import abstractmethod

# Third-Party Packages #
from baseobjects import BaseObject

# Local Packages #


# Definitions #
# Classes #
class LockInterface(BaseObject):
    """An interface which outlines the basis for a lock."""

    # Instance Methods #
    # Lock #
    @abstractmethod
    def acquire(self, block: bool = True, timeout: float | None = None) -> bool:
        """Acquires the lock, waits for the lock if block is True.

        Args:
            block: Determines if this method will block execution while waiting for the lock to be acquired.
            timeout: The time, in seconds, to wait for the lock to be acquired, otherwise returns False.

        Returns:
            If this method successful acquired or failed to a timeout.

        Raises:
            InterruptedError: When this method is interrupted by an interrupt event.
        """

    @abstractmethod
    def release(self) -> None:
        """Release the lock."""

    @abstractmethod
    async def acquire_async(self, block: bool = True, timeout: float | None = None, interval: float = 0.0) -> bool:
        """Asynchronously acquires the lock, waits for the lock if block is True.

        Args:
            block: Determines if this method will block execution while waiting for the lock to be acquired.
            timeout: The time, in seconds, to wait for the lock to be acquired, otherwise returns False.
            interval: The time, in seconds, between each set check.

        Returns:
            If this method successful acquired or failed to a timeout.

        Raises:
            InterruptedError: When this method is interrupted by an interrupt event.
        """

    @abstractmethod
    async def async_context(
        self,
        block: bool = True,
        timeout: float | None = None,
        interval: float = 0.0,
    ) -> "LockInterface":
        """Asynchronous context manager for acquiring and releasing the lock.

        Args:
            block: Determines if this method will block execution while waiting for the lock to be acquired.
            timeout: The time, in seconds, to wait for the lock to be acquired, otherwise returns False.
            interval: The time, in seconds, between each set check.

        Returns:
            This Lock object.
        """
