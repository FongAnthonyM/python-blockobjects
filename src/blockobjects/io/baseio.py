""" baseio.py
An abstract class for IO objects.
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
from collections.abc import Iterable
from typing import Any, NamedTuple, Optional

# Third-Party Packages #
from baseobjects import BaseObject

# Local Packages #


# Definitions #
# Classes #
class IOMap(NamedTuple):
    """The Map and information of an IO object."""
    name: str
    type: Optional[type] = None
    object: Optional["BaseIO"] = None
    links: dict[str, "IOInformation"] | None = None


class BaseIO(BaseObject):
    """An abstract class for IO objects."""

    # Instance Methods #
    # Get
    def get(self, *args, **kwargs) -> Any:
        """Gets the requested item.

        Args:
            *args: The arguments for getting the item.
            **kwargs: The keyword arguments for getting the item.

        Returns:
            The requested item.
        """
        raise NotImplementedError

    # Put
    def put(self, value: Any, *args, **kwargs) -> Any:
        """Puts the requested item.

        Args:
            value: The value to put into this object.
            *args: The arguments for putting the item.
            **kwargs: The keyword arguments for putting the item.
        """
        raise NotImplementedError

    # IO Mapping
    def get_links(self) -> dict[str, IOMap] | Iterable[IOMap, ...] | None:
        """Gets the links of this IO object.

        Returns:
            The links of this IO object.
        """

    def generate_io_map(self) -> IOMap:
        """Generates the IO map of this object

        Returns:
            The IO Map of this object.
        """
        return IOMap(name=self.__class__.__name__, type=self.__class__, object=self, links=self.get_links())
