""" iocontainer.py
An IO object which stores a single value within it.
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
from queue import Empty

# Third-Party Packages #
from baseobjects import search_sentinel

# Local Packages #
from ..base.baseio import BaseIO


# Definitions #
# Classes #
class IOContainer(BaseIO):
    """An IO object which stores a single value within it."""

    # Attributes #
    value: Any = BaseIO.empty_sentinel

    # Instance Methods #
    # State
    def empty(self) -> bool:
        """Returns True if the object is empty, False otherwise."""
        return self.value is self.empty_sentinel

    def poll(self) -> bool:
        """Returns True if the object has something in it, False otherwise."""
        return self.value is not self.empty_sentinel

    # Get
    def get(self, default: Any = search_sentinel, *args, **kwargs) -> Any:
        """Gets the requested item from this container.

        Args:
            default: The default value to return if this container is empty.
            *args: The arguments for getting the item.
            **kwargs: The keyword arguments for getting the item.

        Returns:
            The requested item.

        Raises:
            Empty: When there are no items to get in the queue and there is no default value.
        """
        if self.empty():
            if default is not search_sentinel:
                raise Empty
            else:
                return default
        else:
            value = self.value
            self.value = self.empty_sentinel
            return value

    async def get_async(self, default: Any = search_sentinel, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously gets the requested item from this container.

        Args:
            default: The default value to return if this container is empty.
            *args: The arguments for getting the item.
            **kwargs: The keyword arguments for getting the item.

        Returns:
            The requested item.

        Raises:
            Empty: When there are no items to get in the queue and there is no default value.
        """
        if self.empty():
            if default is not search_sentinel:
                raise Empty
            else:
                return default
        else:
            value = self.value
            self.value = self.empty_sentinel
            return value

    # Put
    def put(self, value: Any, *args, **kwargs) -> None:
        """Puts the requested item into this container.

        Args:
            value: The value to put into this object.
            *args: The arguments for putting the item.
            **kwargs: The keyword arguments for putting the item.
        """
        self.value = value

    async def put_async(self, value: Any, *args: Any, **kwargs: Any) -> None:
        """Asynchronously puts the requested item into this container.

        Args:
            value: The object to put into this object.
            *args: The arguments for putting the item.
            **kwargs: The keyword arguments for putting the item.
        """
        self.value = value
