""" baseio.py
BaseIO is an abstract base class which provides a common interface for all IO Objects. It defines the basic structure
and common methods that all IO Object classes should implement. While it does not implement any specific behavior, it
does define some default attributes.
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
from typing import Any, NamedTuple, Optional
from warnings import warn

# Third-Party Packages #
from baseobjects import BaseObject, SentinelObject
from baseobjects.warnings import NotImplementedWarning

# Local Packages #


# Definitions #
# Classes #
class IOMap(NamedTuple):
    """The Map and information of an IO object."""

    name: str
    type: Optional[type] = None
    object: Optional["BaseIO"] = None
    links: dict[str, "IOMap"] | None = None


class BaseIO(BaseObject):
    """An abstract class for IO objects.

    The BaseIO class and its subclasses (IO Objects) are a systemic tool designed to manage and control data flow
    through inputs and outputs. IO Objects are intended to be used in a variety of contexts, such as data processing and
    application management. The architecture behind the individual IO Objects uses modularity, standardized methods, and
    recursion to give a high degree of control over the routing of the data between IO Objects. When IO Objects are used
    a larger context, they create a network of IO Objects which can be represented through directed graphs.

    IO Objects are also designed to be used in conjunction with multiprocessing frameworks, and together they allow
    multiprocessing applications to be designed as directed graphs.

    BaseIO itself is an abstract base class which provides a common interface for all IO Objects. It defines the basic
    structure and common methods that all IO Object classes should implement. While it does not implement any specific
    behavior, it does define some default attributes.

    Attributes:
        empty_sentinel: A sentinel object representing an empty IO value, which can be used for value handling.
    """

    # Attributes #
    empty_sentinel: SentinelObject = SentinelObject("io_empty")

    # Instance Methods #
    # State
    def empty(self) -> bool:
        """Checks if the IO object is empty.

        Returns:
            True if the IO object is empty, False otherwise.
        """
        raise NotImplementedError

    def poll(self) -> bool:
        """Checks if the IO object has something in it.

        Returns:
            True if the IO object has something in it, False otherwise.
        """
        raise NotImplementedError

    # Get
    def get(self, *args: Any, **kwargs: Any) -> Any:
        """Gets the requested item.

        Args:
            *args: Positional arguments for getting an item.
            **kwargs: Keyword arguments for getting an item.

        Returns:
            The requested item.

        Raises:
            NotImplementedError: This is an abstract method that should be implemented in subclasses.
        """
        raise NotImplementedError

    async def get_async(self, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously gets the requested item.

        Args:
            *args: Positional arguments for getting an item.
            **kwargs: Keyword arguments for getting an item.

        Returns:
            The requested item.

        Raises:
            NotImplementedError: This is an abstract method that should be implemented in subclasses.
        """
        raise NotImplementedError

    # Put
    def put(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        """Puts the requested item.

        Args:
            value: The value to put into this object.
            *args: Positional arguments for putting an item.
            **kwargs: Keyword arguments for putting an item.

        Returns:
            Any result from putting an item.

        Raises:
            NotImplementedError: This is an abstract method that should be implemented in subclasses.
        """
        raise NotImplementedError

    async def put_async(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously puts the requested item.

        Args:
            value: The object to put into this object.
            *args: Positional arguments for putting the item.
            **kwargs: Keyword arguments for putting the item.

        Returns:
            Any result from putting an item.

        Raises:
            NotImplementedError: This is an abstract method that should be implemented in subclasses.
        """
        raise NotImplementedError

    # Join
    def join(self, *args: Any, **kwargs: Any) -> None:
        """Blocks until a condition is met, typically when the IO object is empty."""
        warn(f"{self.__class__} join method", NotImplementedWarning)

    async def join_async(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously blocks until a condition is met, typically when the IO object is empty."""
        warn(f"{self.__class__} join_async method", NotImplementedWarning)

    # IO Mapping
    def get_links(self) -> dict[str, IOMap] | None:
        """Gets the links of this IO object.

        Returns:
            The links of this IO object.

        Raises:
            NotImplementedError: This is an abstract method that should be implemented in subclasses.
        """
        raise NotImplementedError

    def generate_io_map(self) -> IOMap:
        """Generates the IO map of this object

        Returns:
            The IO Map of this object.

        Raises:
            NotImplementedError: This is an abstract method that should be implemented in subclasses.
        """
        raise NotImplementedError
