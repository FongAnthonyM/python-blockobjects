""" contextualevent.py
An object that wraps an event created by a context object and can switch between multiple contexts.
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

# Third-Party Packages #

# Local Packages #
from ....interfaces import EventInterface
from ...bases import BaseProcessingContext, BaseContextualObject


# Definitions #
# Classes #
class ContextualEvent(BaseContextualObject, EventInterface):
    """An object that wraps an event created by a context object and can switch between multiple contexts.

    Attributes:
        event: The event to wrap.
    """
    # Attributes #
    event: EventInterface | None = None

    # Magic Methods #
    # Type Conversion
    def __bool__(self) -> bool:
        """Returns a boolean based on the state of this event."""
        return self.event.is_set()

    # Instance Methods #
    # Constructors/Destructors
    def construct(self, *args: Any, context: BaseProcessingContext | None = None, **kwargs: Any) -> None:
        """Constructs this object.

        Args:
            context: The context of this Queue.
        """
        super().construct(*args, context=context, **kwargs)

        if self.context is not None:
            self.event = self.context.require_event(name=str(id(self)))

    # Context
    def set_context(self, context: BaseProcessingContext) -> None:
        """Sets the context of this object to the given context.

        Args:
            context: The context to assign this object to.
        """
        super().set_context(context=context)

        # Creates a new event and assigns it to the current event state.
        new_event = context.require_event(name=str(id(self)))
        if self.event:
            new_event.set()
        self.event = new_event

    # Event
    def is_set(self) -> bool:
        """Checks if the event is set.

        Returns:
            True if the event is set, otherwise False.
        """
        return self.event.is_set()

    async def is_set_async(self) -> bool:
        """Asynchronously checks if the event is set.

        Returns:
            True if the event is set, otherwise False.
        """
        return await self.event.is_set_async()

    def set(self) -> None:
        """Sets the event."""
        self.event.set()

    def clear(self) -> None:
        """Clears the event."""
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
