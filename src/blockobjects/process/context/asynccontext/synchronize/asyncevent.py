""" asyncevent.py
An Event object using async.
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
from collections import deque
from time import perf_counter

# Third-Party Packages #

# Local Packages #
from ....interfaces import EventInterface


# Definitions #
# Classes #
class AsyncEvent(Event, EventInterface):
    # Magic Methods #
    # Construction/Destruction
    def __init__(self):
        # New Attributes #
        self._holders = deque()

        # Parent Attributes #
        super().__init__()

    # Type Conversion
    def __bool__(self) -> bool:
        """Returns a boolean based on the state of this event."""
        return self.is_set()

    # Instance Methods  #
    # Event
    async def is_set_async(self) -> bool:
        """Asynchronously checks if the event is set.

        Returns:
            True if the event is set, otherwise False.
        """
        return self._value

    def clear(self) -> None:
        """Reset the internal flag to false."""
        if self._value:
            self._value = False

            for fut in self._holders:
                if not fut.done():
                    fut.set_result(True)

    def wait(self, timeout: float | None = None) -> bool:
        """Waits for the Event to be changed to set.

        Args:
            timeout: The time, in seconds, to wait for the Event to be set, otherwise returns False.

        Returns:
            If this method successful waited or failed to a timeout.
        """
        if self._value:
            return True

        fut = self._get_loop().create_future()
        self._waiters.append(fut)

        if timeout is None:
            while True:
                if fut.done():
                    return True
        else:
            deadline = perf_counter() + timeout
            while True:
                if fut.done():
                    self._waiters.remove(fut)
                    return True
                if deadline <= perf_counter():
                    return False

    async def wait_async(self, timeout: float | None = None) -> bool:
        """Asynchronously waits for the Event to be changed to set.

        Args:
            timeout: The time, in seconds, to wait for the Event to be set, otherwise returns False.

        Returns:
            If this method successful waited or failed to a timeout.
        """
        if self._value:
            return True

        fut = self._get_loop().create_future()
        self._waiters.append(fut)

        try:
            await wait_for(fut, timeout)
            return True
        finally:
            self._waiters.remove(fut)

    def hold(self, timeout: float | None = None) -> bool:
        """Waits for the Event to be changed to cleared.

        Args:
            timeout: The time, in seconds, to wait for the Event to be cleared, otherwise returns False.

        Returns:
            If this method successful waited for cleared or failed to a timeout.
        """
        if not self._value:
            return True

        fut = self._get_loop().create_future()
        self._holders.append(fut)

        if timeout is None:
            while True:
                if fut.done():
                    return True
        else:
            deadline = perf_counter() + timeout
            while True:
                if fut.done():
                    self._waiters.remove(fut)
                    return True
                if deadline <= perf_counter():
                    return False

    async def hold_async(self, timeout: float | None = None) -> bool:
        """Asynchronously waits for the Event to be changed to cleared.

        Args:
            timeout: The time, in seconds, to wait for the Event to be cleared, otherwise returns False.

        Returns:
            If this method successful waited for cleared or failed to a timeout.
        """
        if self._value:
            return True

        fut = self._get_loop().create_future()
        self._holders.append(fut)

        try:
            await wait_for(fut, timeout)
            return True
        finally:
            self._waiters.remove(fut)

