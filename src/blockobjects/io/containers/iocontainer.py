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

# Third-Party Packages #

# Local Packages #
from ..base.baseio import BaseIO


# Definitions #
# Classes #
class IOContainer(BaseIO):
    """An IO object which stores a single value within it."""

    # Attributes #
    value: Any = None

    # Magic Methods #
    # Get
    def get(self, *args, **kwargs) -> Any:
        """Gets the requested item from this container.

        Args:
            *args: The arguments for getting the item.
            **kwargs: The keyword arguments for getting the item.

        Returns:
            The requested item.
        """
        value = self.value
        self.value = None
        return value

    async def get_async(self, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously gets the requested item from this container.

        Args:
            *args: The arguments for getting the item.
            **kwargs: The keyword arguments for getting the item.

        Returns:
            The requested item.
        """
        value = self.value
        self.value = None
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
