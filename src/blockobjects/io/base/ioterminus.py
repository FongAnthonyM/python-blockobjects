""" ioterminus.py
An IO Object which is meant to be the terminus of an IO network/graph.
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
from asyncio import Event, wait_for
from time import perf_counter
from typing import Any

# Third-Party Packages #

# Local Packages #
from .baseio import BaseIO


# Definitions #
# Classes #
class IOTerminus(BaseIO):
    """An IO Object which is meant to be the terminus of an IO network/graph.

    Attributes:
        is_joined: An event which is set when the IO object is joined.
        is_empty: A boolean indicating if the IO object is empty.
        get_value: The value to return when get is called.

    Args:
        get_value: The value to return when get is called.
    """

    # Attributes #
    is_joined: Event
    is_empty: bool = True

    get_value: Any = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        get_value: Any = None,
        is_empty: bool = True,
        is_joined: bool = True,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        # New Attributes #
        self.is_joined = Event()
        if is_joined:
            self.is_joined.set()
        else:
            self.is_joined.clear()
        self.is_empty = is_empty

        self.get_value = get_value

        # Parent Attributes #
        super().__init__(*args, **kwargs)

    # Instance Methods #
    # State
    def empty(self) -> bool:
        """Checks if the IO object is empty.

        Returns:
            True if the IO object is empty, False otherwise.
        """
        return self.is_empty

    def poll(self) -> bool:
        """Checks if the IO object has something in it.

        Returns:
            True if the IO object has something in it, False otherwise.
        """
        return not self.is_empty

    # Get
    def get(self, *args: Any, **kwargs: Any) -> Any:
        """Gets an item using the getter function or method.

        Args:
            *args: Positional arguments for getting an item.
            **kwargs: Keyword arguments for getting an item.

        Returns:
            The item returned by the getter function or method.
        """
        return self.get_value

    async def get_async(self, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously gets an item using the getter_async function or method.

        Args:
            *args: Positional arguments for getting an item.
            **kwargs: Keyword arguments for getting an item.

        Returns:
            The item returned by the getter_async function or method.
        """
        return self.get_value

    # Put
    def put(self, value: Any, *args: Any, **kwargs: Any) -> None:
        """Puts an item which drops it silently, since this is the terminus of the IO network/graph.

        Args:
            value: The value to put into this object.
            *args: Positional arguments for putting an item.
            **kwargs: Keyword arguments for putting an item.

        Returns:
            The result of the putter function or method.
        """

    async def put_async(self, value: Any, *args: Any, **kwargs: Any) -> None:
        """Asynchronously puts an item which drops it silently, since this is the terminus of the IO network/graph.

        Args:
            value: The value to put into this object.
            *args: Positional arguments for putting an item.
            **kwargs: Keyword arguments for putting an item.

        Returns:
            The result of the putter function or method.
        """

    # Join
    def join(self, timeout: float | None = None, *args: Any, **kwargs: Any) -> None:
        """Joins when the is_joined event is set.

        Args:
            timeout: The maximum duration in seconds to wait before an error is raised. If None, indefinite blocks.
            *args: Positional arguments for joining.
            **kwargs: Keyword arguments for joining.
        """
        if not self.is_joined.is_set():
            # Determine if there is a timeout
            if timeout is None:
                # Prevent a forever blocking
                raise RuntimeError(f"{self} timeout must be specified, otherwise it will block forever.")
            else:
                # Wait for value to be empty or timeout
                deadline = timeout + perf_counter()
                while not self.is_joined.is_set():
                    if deadline <= perf_counter():
                        raise TimeoutError

    async def join_async(self, timeout: float | None = None, *args: Any, **kwargs: Any) -> None:
        """Asynchronously joins when the is_joined event is set.

        Args:
            timeout: The maximum duration in seconds to wait before an error is raised. If None, indefinite blocks.
            *args: Positional arguments for joining.
            **kwargs: Keyword arguments for joining.
        """
        if not self.is_joined.is_set():
            await wait_for(self.is_joined.wait(), timeout)
