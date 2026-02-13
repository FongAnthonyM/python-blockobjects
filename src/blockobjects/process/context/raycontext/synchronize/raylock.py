"""raylock.py
A Lock object using Ray.

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
from ray import remote, get
from ray.actor import ActorClass, ActorHandle

# Local Packages #
from ....interfaces import LockInterface
from ...asynccontext import AsyncLock


# Definitions #
# Classes #
class RayLock(LockInterface):
    """A Lock object using Ray.

    Attributes:
        _remote_lock_class: The Ray actor class used to create the remote lock.
        _remote_lock: The remote lock.
    """
    # Attributes #
    _remote_lock_class: ActorClass = remote(num_cpus=0)(AsyncLock)
    _remote_lock: ActorHandle | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Attributes #
        self._remote_event = self._remote_lock_class.remote()

        # Construction #
        super().__init__(*args, **kwargs)

    # Context Manager
    def __enter__(self):
        self._remote_lock.aquire.remote()
        return None

    def __exit__(self, exc_type, exc, tb):
        self._remote_lock.release.remote()

    async def __aenter__(self):
        await self._remote_lock.aquire_async.remote()
        return None

    async def __aexit__(self, exc_type, exc, tb):
        self._remote_lock.release.remote()

    # Instance Methods #
    def locked(self) -> bool:
        """Return True if lock is acquired."""
        return get(self._remote_lock.locked.remote())

    def acquire(self, block: bool = True, timeout: float | None = None) -> bool:
        """Acquires the Lock, waits for the lock if block is True.

        Args:
            block: Determines if this method will block execution while waiting for the lock to be acquired.
            timeout: The time, in seconds, to wait for the lock to be acquired, otherwise returns False.

        Returns:
            If this method successful acquired or failed to a timeout.
        """
        return get(self._remote_lock.aquire.remote(block, timeout))

    async def acquire_async(self, block: bool = True, timeout: float | None = None, interval: float = 0.0) -> bool:
        """Asynchronously acquires the Lock, waits for the lock if block is True.

        Args:
            block: Determines if this method will block execution while waiting for the lock to be acquired.
            timeout: The time, in seconds, to wait for the lock to be acquired, otherwise returns False.
            interval: The time, in seconds, between each set check.

        Returns:
            If this method successful acquired or failed to a timeout.
        """
        return await self._remote_lock.aquire_async.remote(block, timeout, interval)

    def release(self) -> None:
        """Releases the Lock."""
        self._remote_lock.release.remote()

    @contextmanager
    async def async_context(self, block: bool = True, timeout: float | None = None, interval: float = 0.0) -> "RayLock":
        """Asynchronous context manager for acquiring and releasing the Lock.

        Args:
            block: Determines if this method will block execution while waiting for the lock to be acquired.
            timeout: The time, in seconds, to wait for the lock to be acquired, otherwise returns False.
            interval: The time, in seconds, between each set check.

        Returns:
            This Lock object.
        """
        try:
            await self._remote_lock.aquire_async.remote(block, timeout, interval)
            yield self
        finally:
            self._remote_lock.release.remote()
