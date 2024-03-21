""" iodelegator.py
An IO object which delegates io to another io object.
"""
# Package Header #
from ..header import *

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
from .baseio import BaseIO


# Definitions #
# Classes #
class IODelegator(BaseIO):
    """An IO object which stores a single value within it.

    Args:
        *args: Arguments for inheritance.
        **kwargs: Keyword arguments for inheritance.
    """

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, io_: BaseIO | None = None, *args: Any, **kwargs: Any) -> None:
        # New Attributes #
        self.io: BaseIO | None = io_

        # Parent Attributes #
        super().__init__(*args, **kwargs)

    def get_last_io(self) -> BaseIO | None:
        """Recursively gets the last IO object which is not an IODelegator.

        Returns:
            An IO object which is not an IODelegator.
        """
        return self.io.get_last_io() if isinstance(self.io, IODelegator) else self.io

    # Get
    def get(self, *args, **kwargs) -> Any:
        """Gets the requested item from another IO object.

        Args:
            *args: The arguments for getting the item.
            **kwargs: The keyword arguments for getting the item.

        Returns:
            The requested item.
        """
        return self.get_last_io().get(*args, **kwargs)

    async def get_async(self, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously gets the requested item from another IO object.

        Args:
            *args: The arguments for getting the item.
            **kwargs: The keyword arguments for getting the item.

        Returns:
            The requested item.
        """
        return await self.get_last_io().get_async(*args, **kwargs)

    # Put
    def put(self, value: Any, *args, **kwargs) -> None:
        """Puts the requested item into another IO object.

        Args:
            value: The value to put into this object.
            *args: The arguments for putting the item.
            **kwargs: The keyword arguments for putting the item.
        """
        self.get_last_io().put(value, *args, **kwargs)

    async def put_async(self, value: Any, *args: Any, **kwargs: Any) -> None:
        """Asynchronously puts the requested item into another IO object.

        Args:
            value: The object to put into this object.
            *args: The arguments for putting the item.
            **kwargs: The keyword arguments for putting the item.
        """
        await self.get_last_io().put_async(value, *args, **kwargs)
