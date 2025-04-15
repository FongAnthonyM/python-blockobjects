""" iocontainer.py
An IO Object which stores a single value within it.
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
from asyncio import sleep
from time import perf_counter
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
            *args: Positional arguments for getting an item.
            **kwargs: Keyword arguments for getting an item.

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
            *args: Positional arguments for getting an item.
            **kwargs: Keyword arguments for getting an item.

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
            *args: Positional arguments for putting an item.
            **kwargs: Keyword arguments for putting an item.
        """
        self.value = value

    async def put_async(self, value: Any, *args: Any, **kwargs: Any) -> None:
        """Asynchronously puts a value into this container.

        Args:
            value: The object to put into this object.
            *args: Positional arguments for putting an item.
            **kwargs: Keyword arguments for putting an item.
        """
        self.value = value

    # Join
    def join(self, timeout: float | None = None, *args: Any, **kwargs: Any) -> None :
        """Blocks until the object has completed or the timeout expires.

        Args:
            timeout: The maximum duration in seconds to wait before an error is raised. If None, indefinite blocking
                is prohibited, and a `RuntimeError` is raised.
            *args: Positional arguments for inheritance.
            **kwargs: Keyword arguments for inheritance.

        Raises:
            RuntimeError: Raised when a timeout is not specified and the `value` attribute is still the `empty_sentinel`
            TimeoutError: Raised when the timeout expires before the thread has completed its execution
        """
        # Check if the object is empty
        if self.value is self.empty_sentinel:
            return

        # Determine if there is a timeout
        if timeout is None:
            # Prevent a forever blocking
            raise RuntimeError(f"{self} timeout must be specified, otherwise it will block forever.")
        else:
            # Wait for value to be empty or timeout
            deadline = timeout + perf_counter()
            while self.value is not self.empty_sentinel:
                if deadline <= perf_counter():
                    raise TimeoutError

    async def join_async(self, timeout: float | None = None, interval: float = 0.0, *args: Any, **kwargs: Any) -> None:
        """Asynchronously, blocks the until the object has completed or the timeout expires.

        Args:
            timeout: The maximum duration in seconds to wait before an error is raised. If None, indefinite blocks.
            interval: The interval in seconds between successive checks of the object's value.
            *args: Positional arguments for inheritance.
            **kwargs: Keyword arguments for inheritance.

        Raises:
            TimeoutError: If object's value does not become the empty sentinel within the specified duration.
        """
        # Check if the object is empty
        if self.value is self.empty_sentinel:
            return

        # Determine if there is a timeout
        if timeout is None:
            # Wait for value to be empty
            while self.value is not self.empty_sentinel:
                await sleep(interval)
        else:
            # Wait for value to be empty or timeout
            deadline = timeout + perf_counter()
            while self.value is not self.empty_sentinel:
                await sleep(interval)
                if deadline <= perf_counter():
                    raise TimeoutError
