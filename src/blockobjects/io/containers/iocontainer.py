""" iocontainer.py
An IO Object which stores a single value within it.
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
from baseobjects import SentinelObject, search_sentinel

# Local Packages #
from ..base.baseio import BaseIO


# Definitions #
# Classes #
class IOContainer(BaseIO):
    """An IO Object which stores a single value within it.

    Attributes:
        value: The value stored within this container.
    """

    # Attributes #
    value: Any = BaseIO.empty_sentinel

    # Instance Methods #
    # State
    def empty(self) -> bool:
        """Checks if the container is empty.

        Returns:
            bool: True if the container is empty, False otherwise.
        """
        return self.empty_sentinel == self.value

    def poll(self) -> bool:
        """Checks if the container has a value.

        Returns:
            bool: True if the container has a value, False otherwise.
        """
        return not self.empty_sentinel == self.value

    # Get
    def get(self, default: Any = search_sentinel, *args, **kwargs) -> Any:
        """Gets the value from this container.

        Args:
            default: The default value to return if this container is empty.
            *args: Variable length argument list for getting an item.
            **kwargs: Arbitrary keyword arguments for getting an item.

        Returns:
            Any: The value from the container.

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
        """Asynchronously gets the value from this container.

        Args:
            default: The default value to return if this container is empty.
            *args: Variable length argument list for getting an item.
            **kwargs: Arbitrary keyword arguments for getting an item.

        Returns:
            The value from the container.

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
        """Puts a value into this container.

        Args:
            value: The value to put into this object.
            *args: Variable length argument list for putting an item.
            **kwargs: Arbitrary keyword arguments for putting an item.
        """
        self.value = value

    async def put_async(self, value: Any, *args: Any, **kwargs: Any) -> None:
        """Asynchronously puts a value into this container.

        Args:
            value: The object to put into this object.
            *args: Variable length argument list for putting an item.
            **kwargs: Arbitrary keyword arguments for putting an item.
        """
        self.value = value
