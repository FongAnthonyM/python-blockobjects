""" rayevent.py
An Event object using Ray.
"""
# Package Header #
from ...header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Standard Libraries #
from typing import Any

# Third-Party Packages #
from ray import remote, get
from ray.actor import ActorClass, ActorHandle
from src.blockobjects.process.asynccontext import AsyncEvent

# Local Packages #
from src.blockobjects.process.context import EventInterface


# Definitions #
# Classes #
class RayEvent(EventInterface):
    """An Event object using Ray.

    Attributes:
        _remote_event_class: The Ray actor class used to create the remote event.
        _remote_event: The remote event.
    """
    # Attributes #
    _remote_event_class: ActorClass = remote(num_cpus=0)(AsyncEvent)
    _remote_event: ActorHandle | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # Attributes #
        self._remote_event = self._remote_event_class.remote()

        # Construction #
        super().__init__(*args, **kwargs)

    # Type Conversion
    def __bool__(self) -> bool:
        """Returns a boolean based on the state of this event."""
        return self.is_set()

    # Instance Methods  #
    # Event
    def is_set(self) -> bool:
        """Checks if the event is set."""
        return get(self._remote_event.is_set.remote())

    async def is_set_async(self) -> bool:
        """Asynchronously checks if the event is set.

        Returns:
            True if the event is set, otherwise False.
        """
        return await self._remote_event.is_set.remote()

    def set(self) -> None:
        """Sets the event."""
        self._remote_event.set.remote()

    def clear(self) -> None:
        """Clears the event."""
        self._remote_event.clear.remote()

    def wait(self, timeout: float | None = None) -> bool:
        """Waits for the Event to be changed to set.

        Args:
            timeout: The time, in seconds, to wait for the Event to be set, otherwise returns False.

        Returns:
            If this method successful waited or failed to a timeout.
        """
        return get(self._remote_event.wait.remote(timeout))

    async def wait_async(self, timeout: float | None = None, interval: float = 0.0) -> bool:
        """Asynchronously waits for the Event to be changed to set.

        Args:
            timeout: The time, in seconds, to wait for the Event to be set, otherwise returns False.
            interval: The time, in seconds, between each set check.

        Returns:
            If this method successful waited or failed to a timeout.
        """
        return await self._remote_event.wait_async.remote(timeout, interval)

    def hold(self, timeout: float | None = None) -> bool:
        """Waits for the Event to be changed to cleared.

        Args:
            timeout: The time, in seconds, to wait for the Event to be cleared, otherwise returns False.

        Returns:
            If this method successful waited for cleared or failed to a timeout.
        """
        return get(self._remote_event.hold.remote(timeout))

    async def hold_async(self, timeout: float | None = None, interval: float = 0.0) -> bool:
        """Waits for the Event to be changed to cleared.

        Args:
            timeout: The time, in seconds, to wait for the Event to be cleared, otherwise returns False.
            interval: The time, in seconds, between each set check.

        Returns:
            If this method successful waited for cleared or failed to a timeout.
        """
        return await self._remote_event.hold_async.remote(timeout, interval)
