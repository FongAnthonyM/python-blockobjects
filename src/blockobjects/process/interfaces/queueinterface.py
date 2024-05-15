""" queueinterface.py
An interface which outlines the basis for an async queue.
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
from baseobjects import BaseObject

# Local Packages #


# Definitions #
# Classes #
class QueueInterface(BaseObject):
    """An interface which outlines the basis for an async queue."""

    # Instance Methods #
    # State
    def empty(self) -> bool:
        """Returns True if the queue is empty, False otherwise."""
        raise NotImplemented

    def poll(self) -> bool:
        """Returns True if the queue has something in it, False otherwise."""
        raise NotImplementedError

    # Get
    def get(self, block: bool = True, timeout: float | None = None, *args: Any, **kwargs: Any) -> Any:
        """Gets an item from the queue."""
        raise NotImplemented

    async def get_async(
        self,
        block: bool = True,
        timeout: float | None = None,
        interval: float = 0.0,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Asynchronously gets an item from the queue."""
        raise NotImplemented

    # Put
    def put(self, value: Any, *args: Any, **kwargs: Any) -> None:
        """Puts an item on the queue."""
        raise NotImplemented

    async def put_async(
        self,
        value: Any,
        timeout: float | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Asynchronously puts an item on the queue."""
        raise NotImplemented

    # Join
    def join(self) -> None:
        """Blocks until all items in the Queue have been gotten."""
        pass

    async def join_async(self) -> None:
        """Asynchronously, blocks until all items in the Queue have been gotten.

        Args:
            interval: The time, in seconds, between each queue check.
        """
        pass
