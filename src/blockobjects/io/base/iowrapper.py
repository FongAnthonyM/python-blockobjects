"""iowrapper.py
An IO Object which wraps other functions or methods as an IO Object.

"""

# Header #
__package_name__ = "blockobjects"

__author__ = "Anthony Fong"
__credits__ = ["Anthony Fong"]
__copyright__ = "Copyright 2022, Anthony Fong"
__license__ = "MIT"

__version__ = "0.1.0"


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
        joiner: A function or method that is used to join.
        joiner_async: An asynchronous function or method that is used to join.
        *args: Positional arguments.
        **kwargs: Keyword arguments.
    """

    # Attributes #
    getter: AnyCallable | None = None
    getter_async: AnyCallable | None = None
    putter: AnyCallable | None = None
    putter_async: AnyCallable | None = None
    joiner: AnyCallable | None = None
    joiner_async: AnyCallable | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        getter: AnyCallable | None = None,
        getter_async: AnyCallable | None = None,
        putter: AnyCallable | None = None,
        putter_async: AnyCallable | None = None,
        joiner: AnyCallable | None = None,
        joiner_async: AnyCallable | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        # New Attributes #
        self.getter = getter
        self.getter_async = getter_async
        self.putter = putter
        self.putter_async = putter_async
        self.joiner = joiner
        self.joiner_async = joiner_async

        # Parent Attributes #
        super().__init__(*args, **kwargs)

    # Instance Methods #
    # Get
    def get(self, *args: Any, **kwargs: Any) -> Any:
        """Gets an item using the getter function or method.

        Args:
            *args: Positional arguments for getting an item.
            **kwargs: Keyword arguments for getting an item.

        Returns:
            The item returned by the getter function or method.
        """
        return self.getter(*args, **kwargs)

    async def get_async(self, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously gets an item using the getter_async function or method.

        Args:
            *args: Positional arguments for getting an item.
            **kwargs: Keyword arguments for getting an item.

        Returns:
            The item returned by the getter_async function or method.
        """
        return await self.getter_async(*args, **kwargs)

    # Put
    def put(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        """Puts an item using the putter function or method.

        Args:
            value: The value to put into this object.
            *args: Positional arguments for putting an item.
            **kwargs: Keyword arguments for putting an item.

        Returns:
            The result of the putter function or method.
        """
        return self.putter(value, *args, **kwargs)

    async def put_async(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously puts an item using the putter function or method.

        Args:
            value: The value to put into this object.
            *args: Positional arguments for putting an item.
            **kwargs: Keyword arguments for putting an item.

        Returns:
            The result of the putter function or method.
        """
        return await self.putter_async(value, *args, **kwargs)

    # Join
    def join(self, *args: Any, **kwargs: Any) -> None:
        """Joins using the joiner function or method.

        Args:
            *args: Positional arguments for joining.
            **kwargs: Keyword arguments for joining.
        """
        return self.joiner(*args, **kwargs)

    async def join_async(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously joins using the joiner_async function or method.

        Args:
            *args: Positional arguments for joining.
            **kwargs: Keyword arguments for joining.
        """
        return await self.joiner_async(*args, **kwargs)
