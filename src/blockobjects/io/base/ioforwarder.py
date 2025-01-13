""" ioforwarder.py
IOForwarder forwards IO to another IO object. It is essentially a wrapper for other IO Objects, but it can change which
IO Object it is wrapping at any time. This is useful for changing the routing of the IO data during runtime. The two
main uses of this type of routing redirection is to either change routing due to state change in the system and/or
refactor the IO routing to more direct links. IOForwarder is primarily intended to be used to refactor the IO routing as
it reduces the overhead of passing data between multiple IO Objects, especially when the data is being passed linearly.
While IOForwarder can be used to redirect routing due to state changes, this is not advised since it can be difficult to
track the routing of the data. IORouter should be used for routing redirection instead, because it is designed to handle
complex routing redirection.
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
from .baseio import BaseIO


# Definitions #
# Classes #
class IOForwarder(BaseIO):
    """An IO Object which forwards IO to another IO Object.

    IOForwarder is a wrapper for other IO Objects, but it can change which IO Object it is wrapping at any time. This is
    useful for changing the routing of the IO data during runtime. The two main uses of this type of routing redirection
    is to either change routing due to state change in the system and/or refactor the IO routing to more direct links.
    IOForwarder is primarily intended to be used to refactor the IO routing as it reduces the overhead of passing data
    between multiple IO Objects, especially when the data is being passed linearly. While IOForwarder can be used to
    redirect routing due to state changes, this is not advised since it can be difficult to track the routing of the
    data. IORouter should be used for routing redirection instead, because it is designed to handle complex routing
    redirection.

    Attributes:
        io: The IO object to arbitrate to.

    Args:
        io_: The IO object to arbitrate to.
        *args: Arguments for inheritance.
        **kwargs: Keyword arguments for inheritance.
    """

    # Attributes #
    io: BaseIO | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, io_: BaseIO | None = None, *args: Any, **kwargs: Any) -> None:
        # New Attributes #
        self.io = io_

        # Parent Attributes #
        super().__init__(*args, **kwargs)

    # IO
    def get_last_io(self) -> BaseIO | None:
        """Recursively gets the last IO Object which is not an IOForwarder.

        Returns:
            An IO object which is not an IOForwarder.
        """
        return self.io.get_last_io() if isinstance(self.io, IOForwarder) else self.io

    # Get
    def get(self, *args: Any, **kwargs: Any) -> Any:
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
            *args: Positional arguments for getting an item.
            **kwargs: Keyword arguments for getting an item.

        Returns:
            The requested item.
        """
        return await self.get_last_io().get_async(*args, **kwargs)

    # Put
    def put(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        """Puts the requested item into another IO object.

        Args:
            value: The value to put into this object.
            *args: Positional arguments for putting an item.
            **kwargs: Keyword arguments for putting an item.
        """
        return self.get_last_io().put(value, *args, **kwargs)

    async def put_async(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously puts the requested item into another IO object.

        Args:
            value: The object to put into this object.
            *args: Positional arguments for putting an item.
            **kwargs: Keyword arguments for putting an item.
        """
        return await self.get_last_io().put_async(value, *args, **kwargs)

    # Join
    def join(self, *args: Any, **kwargs: Any) -> None:
        """Joins another IO object.

        Args:
            *args: Positional arguments for joining an IO object.
            **kwargs: Keyword arguments for joining an IO object.
        """
        return self.get_last_io().join(*args, **kwargs)

    async def join_async(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously joins another IO object.

        Args:
            *args: Positional arguments for joining an IO object.
            **kwargs: Keyword arguments for joining an IO object.
        """
        return await self.get_last_io().join_async(*args, **kwargs)
