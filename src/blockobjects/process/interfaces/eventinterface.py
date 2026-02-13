"""eventinterface.py
An interface which outlines the basis for an event.

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
from abc import abstractmethod

# Third-Party Packages #
from baseobjects import BaseObject

# Local Packages #


# Definitions #
# Classes #
class EventInterface(BaseObject):
    """An interface which outlines the basis for an event."""

    # Magic Methods #
    # Type Conversion
    @abstractmethod
    def __bool__(self) -> bool:
        """Returns a boolean based on the state of this event."""

    # Instance Methods #
    # Event
    @abstractmethod
    def is_set(self) -> bool:
        """Checks if the event is set.

        Returns:
            True if the event is set, otherwise False.
        """

    @abstractmethod
    async def is_set_async(self) -> bool:
        """Asynchronously checks if the event is set.

        Returns:
            True if the event is set, otherwise False.
        """

    @abstractmethod
    def set(self) -> None:
        """Sets the event."""

    @abstractmethod
    def clear(self) -> None :
        """Clears the event."""

    @abstractmethod
    def wait(self, timeout: float | None = None) -> bool:
        """Waits for the event to be changed to set.

        Args:
            timeout: The time, in seconds, to wait for the ContextualEvent to be set, otherwise returns False.

        Returns:
            If this method successful waited or failed to a timeout.
        """

    @abstractmethod
    async def wait_async(self, timeout: float | None = None) -> bool:
        """Asynchronously waits for the event to be changed to set.

        Args:
            timeout: The time, in seconds, to wait for the ContextualEvent to be set, otherwise returns False.

        Returns:
            If this method successful waited or failed to a timeout.
        """

    @abstractmethod
    def hold(self, timeout: float | None = None) -> bool:
        """Waits for the event to be changed to cleared.

        Args:
            timeout: The time, in seconds, to wait for the ContextualEvent to be cleared, otherwise returns False.

        Returns:
            If this method successful waited for cleared or failed to a timeout.
        """

    @abstractmethod
    async def hold_async(self, timeout: float | None = None) -> bool:
        """Waits for the event to be changed to cleared.

        Args:
            timeout: The time, in seconds, to wait for the ContextualEvent to be cleared, otherwise returns False.

        Returns:
            If this method successful waited for cleared or failed to a timeout.
        """
