""" iowrapper.py
An IO object which wraps another function io object.
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
from collections.abc import Callable
from typing import Any

# Third-Party Packages #
from baseobjects.typing import AnyCallable

# Local Packages #
from .baseio import BaseIO


# Definitions #
# Classes #
class IOWrapper(BaseIO):
    """An IO object which stores a single value within it.

    Args:
        *args: Arguments for inheritance.
        **kwargs: Keyword arguments for inheritance.
    """

    # Attributes #
    getter: AnyCallable | None = None
    getter_async: AnyCallable | None = None
    putter: AnyCallable | None = None
    putter_async: AnyCallable | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        getter: AnyCallable | None = None,
        getter_async: AnyCallable | None = None,
        putter: AnyCallable | None = None,
        putter_async: AnyCallable | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        # New Attributes #
        self.getter = getter
        self.getter_async = getter_async
        self.putter = putter
        self.putter_async = putter_async

        # Parent Attributes #
        super().__init__(*args, **kwargs)

    # Instance Methods #
    # Get
    def get(self, *args, **kwargs) -> Any:
        """Gets the requested item from another IO object.

        Args:
            *args: The arguments for getting the item.
            **kwargs: The keyword arguments for getting the item.

        Returns:
            The requested item.
        """
        try:
            return self.getter(*args, **kwargs)
        except AttributeError:
            raise AttributeError(f"{self} has no getter")

    async def get_async(self, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously gets the requested item from another IO object.

        Args:
            *args: The arguments for getting the item.
            **kwargs: The keyword arguments for getting the item.

        Returns:
            The requested item.
        """
        try:
            return await self.getter_async(*args, **kwargs)
        except AttributeError:
            raise AttributeError(f"{self} has no getter_async")

    # Put
    def put(self, value: Any, *args, **kwargs) -> Any:
        """Puts the requested item into another IO object.

        Args:
            value: The value to put into this object.
            *args: The arguments for putting the item.
            **kwargs: The keyword arguments for putting the item.
        """
        try:
            return self.putter(value, *args, **kwargs)
        except AttributeError:
            raise AttributeError(f"{self} has no putter")

    async def put_async(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously puts the requested item into another IO object.

        Args:
            value: The object to put into this object.
            *args: The arguments for putting the item.
            **kwargs: The keyword arguments for putting the item.
        """
        try:
            return await self.putter_async(value, *args, **kwargs)
        except AttributeError:
            raise AttributeError(f"{self} has no putter_async")
