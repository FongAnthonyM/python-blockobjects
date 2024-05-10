""" iowrapper.py
An IO Object which wraps other functions or methods as an IO Object.
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
from baseobjects.typing import AnyCallable

# Local Packages #
from .baseio import BaseIO


# Definitions #
# Classes #
class IOWrapper(BaseIO):
    """An IO Object which wraps other functions or methods as an IO Object.

    Attributes:
        getter: A function or method that is used to get data.
        getter_async: An asynchronous function or method that is used to get data.
        putter: A function or method that is used to put data.
        putter_async: An asynchronous function or method that is used to put data.

    Args:
        getter: A function or method that is used to get data.
        getter_async: An asynchronous function or method that is used to get data.
        putter: A function or method that is used to put data.
        putter_async: An asynchronous function or method that is used to put data.
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
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
    def get(self, *args: Any, **kwargs: Any) -> Any:
        """Gets an item using the getter function or method.

        Args:
            *args: Variable length argument list for getting an item.
            **kwargs: Arbitrary keyword arguments for getting an item.

        Returns:
            The item returned by the getter function or method.

        Raises:
            AttributeError: If the getter function or method is not set.
        """
        try:
            return self.getter(*args, **kwargs)
        except AttributeError:
            raise AttributeError(f"{self} has no getter")

    async def get_async(self, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously gets an item using the getter_async function or method.

        Args:
            *args: Variable length argument list for getting an item.
            **kwargs: Arbitrary keyword arguments for getting an item.

        Returns:
            The item returned by the getter_async function or method.

        Raises:
            AttributeError: If the getter_async function or method is not set.
        """
        try:
            return await self.getter_async(*args, **kwargs)
        except AttributeError:
            raise AttributeError(f"{self} has no getter_async")

    # Put
    def put(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        """Puts an item using the putter function or method.

        Args:
            value: The value to put into this object.
            *args: Variable length argument list for putting an item.
            **kwargs: Arbitrary keyword arguments for putting an item.

        Returns:
            The result of the putter function or method.

        Raises:
            AttributeError: If the putter function or method is not set.
        """
        try:
            return self.putter(value, *args, **kwargs)
        except AttributeError:
            raise AttributeError(f"{self} has no putter")

    async def put_async(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously puts an item using the putter function or method.

        Args:
            value: The value to put into this object.
            *args: Variable length argument list for putting an item.
            **kwargs: Arbitrary keyword arguments for putting an item.

        Returns:
            The result of the putter function or method.

        Raises:
            AttributeError: If the putter function or method is not set.
        """
        try:
            return await self.putter_async(value, *args, **kwargs)
        except AttributeError:
            raise AttributeError(f"{self} has no putter_async")
