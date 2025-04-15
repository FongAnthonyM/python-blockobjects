""" queueinterface.py
An interface which outlines the basis for an async queue.
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
from typing import Any

# Third-Party Packages #
from baseobjects import BaseObject

# Local Packages #


# Definitions #
# Classes #
class QueueInterface(BaseObject):
    """An interface which outlines the basis for an async queue."""

    # Instance Methods #
    # State
    def empty(self) -> bool:
        """Returns True if the queue is empty, False otherwise."""
        raise NotImplementedError

    def poll(self) -> bool:
        """Returns True if the queue has something in it, False otherwise."""
        raise NotImplementedError

    # Size
    def set_maxsize(self, maxsize: int) -> None:
        """Sets the maximum size allowed for the queue.

        This method sets the maximum size of the queue by invoking the underlying set_maxsize method. This value
        determines the total number of elements the queue can hold.

        Args:
            maxsize: The maximum size to set for the queue.
        """
        raise NotImplementedError

    def get_maxsize(self) -> int:
        """Gets the maximum size of the queue.

        This method returns the maximum number of items that the queue can hold. It is useful for determining
        capacity constraints of the queue in a specific scenario.

        Returns:
            int: The maximum size of the queue.
        """
        raise NotImplementedError

    # Get
    def get(self, block: bool = True, timeout: float | None = None, *args: Any, **kwargs: Any) -> Any:
        """Gets an item from the queue."""
        raise NotImplemented

    async def get_async(
        self,
        block: bool = True,
        timeout: float | None = None,
        interval: float = 0.0,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Asynchronously gets an item from the queue."""
        raise NotImplemented

    # Put
    def put(self, value: Any, *args: Any, **kwargs: Any) -> None:
        """Puts an item on the queue."""
        raise NotImplemented

    async def put_async(
        self,
        value: Any,
        timeout: float | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Asynchronously puts an item on the queue."""
        raise NotImplemented

    # Join
    def join(self, *args: Any, **kwargs: Any) -> None:
        """Blocks until all items in the Queue have been gotten."""
        pass

    async def join_async(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously, blocks until all items in the Queue have been gotten."""
        pass
