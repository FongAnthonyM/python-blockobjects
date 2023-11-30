""" iocontainer.py
An IO object which stores a single value within it.
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
class IOContainer(BaseIO):
    """An IO object which stores a single value within it.

    Args:
        *args: Arguments for inheritance.
        **kwargs: Keyword arguments for inheritance.
    """
    # Magic Methods #
    # Construction/Destruction
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # New Attributes #
        self.value: Any = None

        # Parent Attributes #
        super().__init__(*args, **kwargs)

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

    # Put
    def put(self, value: Any, *args, **kwargs) -> None:
        """Puts the requested item into this container.

        Args:
            value: The value to put into this object.
            *args: The arguments for putting the item.
            **kwargs: The keyword arguments for putting the item.
        """
        self.value = value
