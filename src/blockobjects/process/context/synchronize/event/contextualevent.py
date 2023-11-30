""" contextualevent.py

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

# Third-Party Packages #

# Local Packages #
from ...baseprocesscontext import BaseProcessContext
from ...contextualobject import ContextualObject
from .eventinterface import EventInterface


# Definitions #
# Classes #
class ContextualEvent(ContextualObject, EventInterface):
    """
    """

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, *, context: BaseProcessContext | None = None, init: bool = True) -> None:
        # New Attributes #
        self.event = None

        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct(context=context)

    # Type Conversion
    def __bool__(self) -> bool:
        """Returns a boolean based on the state of this event."""
        return self.event.is_set()

    # Instance Methods #
    # Context #
    def set_context(self, context: BaseProcessContext) -> None:
        super().set_context(context=context)
        new_event = context.create_event()
        if self.event:
            new_event.set()
        self.event = new_event

    # Event #
    def is_set(self):
        return self.event.is_set

    def set(self):
        self.event.set()

    def clear(self):
        self.event.clear()

    def wait(self, timeout: float | None = None) -> bool:
        """Waits for the ContextualEvent to be changed to set.

        Args:
            timeout: The time, in seconds, to wait for the ContextualEvent to be set, otherwise returns False.

        Returns:
            If this method successful waited or failed to a timeout.

        Raises:
            InterruptedError: When this method is interrupted by an interrupt event.
        """
        return self.event.wait(timeout=timeout)

    async def wait_async(self, timeout: float | None = None, interval: float = 0.0) -> bool:
        """Asynchronously waits for the ContextualEvent to be changed to set.

        Args:
            timeout: The time, in seconds, to wait for the ContextualEvent to be set, otherwise returns False.
            interval: The time, in seconds, between each set check.

        Returns:
            If this method successful waited or failed to a timeout.

        Raises:
            InterruptedError: When this method is interrupted by an interrupt event.
        """
        return await self.event.wait_async(timeout=timeout, interval=interval)

    def hold(self, timeout: float | None = None) -> bool:
        """Waits for the ContextualEvent to be changed to cleared.

        Args:
            timeout: The time, in seconds, to wait for the ContextualEvent to be cleared, otherwise returns False.

        Returns:
            If this method successful waited for cleared or failed to a timeout.
        """
        return self.event.hold(timeout=timeout)

    async def hold_async(self, timeout: float | None = None, interval: float = 0.0) -> bool:
        """Waits for the ContextualEvent to be changed to cleared.

        Args:
            timeout: The time, in seconds, to wait for the ContextualEvent to be cleared, otherwise returns False.
            interval: The time, in seconds, between each set check.

        Returns:
            If this method successful waited for cleared or failed to a timeout.

        Raises:
            InterruptedError: When this method is interrupted by an interrupt event.
        """
        return await self.hold_async(timeout=timeout, interval=interval)
