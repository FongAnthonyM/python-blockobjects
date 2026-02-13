"""multiprocessingqueue.py
Extends the multiprocessing Queue by adding async methods and interrupts for blocking methods.

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
from multiprocessing import get_context
from multiprocessing.queues import Queue
from multiprocessing.context import BaseContext
from multiprocessing.reduction import ForkingPickler
from queue import Empty, Full
from time import perf_counter
from typing import ClassVar, Any

# Third-Party Packages #
from baseobjects import BaseReducible
from baseobjects import search_sentinel

# Local Packages #
from ....interfaces import QueueInterface
from ..synchronize import MultiProcessingInterrupt


# Definitions #
# Classes #
class MultiProcessingQueue(Queue, QueueInterface, BaseReducible):
    """Extends the multiprocessing Queue by adding async methods and interrupts for blocking methods.

    Class Attributes:
        _ignore_attributes: The attributes to not pickle when pickling.

    Attributes:
        get_interrupt: An event which can be set to interrupt the get method blocking.
        put_interrupt: An event which can be set to interrupt the ptt method blocking.
        space_wait: Determines if this queue will wait for the queue space to enqueue an item.

    Args:
        maxsize: The maximum number items that can be in the queue.
        space_wait: Determines if this queue will wait for the queue space to enqueue an item.
        ctx: The context for the Python multiprocessing.
    """
    # Class Attributes #
    _ignore_attributes: ClassVar[set[str]] = set(Queue(ctx=get_context()).__dict__.keys())

    # Attributes #
    get_interrupt: MultiProcessingInterrupt
    put_interrupt: MultiProcessingInterrupt
    space_wait: bool = True

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, maxsize: int = 0, space_wait: bool = True, *, ctx: BaseContext | None = None) -> None:
        # New Attributes #
        self.get_interrupt = MultiProcessingInterrupt()
        self.put_interrupt = MultiProcessingInterrupt()

        self.space_wait: bool = space_wait

        # Construction #
        super().__init__(maxsize=maxsize, ctx=get_context() if ctx is None else ctx)

    # Pickling
    def __getstate__(self) -> None | dict[str, Any] | tuple[dict[str, Any] | None, dict[str, Any]]:
        """Gets the object's state for pickling.

        Returns:
            The state returned will be either of the following types based on the presence of __dict__ and __slots__:
                None: __dict__ nor __slots__ are present.
                dict: __dict__ is present and __slots__ is not present.
                tuple[None, dict]: __dict__ is not present and __slots__ is present.
                tuple[dict, dict]: __dict__ is present and __slots__ is present.
        """
        state = super().__getstate__()
        for name in self._ignore_attributes:
            del state[name]
        return Queue.__getstate__(self), state

    def __setstate__(self, state: Any) -> None:
        """Builds this object based on a dictionary of corresponding attributes.

        Args:
            state: The attributes to build this object from.
        """
        Queue.__setstate__(self, state[0])
        self.__dict__.update(state[1])

    # Instance Methods #
    # State
    def poll(self) -> bool:
        """Returns True if the queue has something in it, False otherwise."""
        return self._poll()

    # Size
    def set_maxsize(self, maxsize: int) -> None:
        """Sets the maximum size allowed for the queue.

        This method sets the maximum size of the queue by invoking the underlying set_maxsize method. This value
        determines the total number of elements the queue can hold.

        Args:
            maxsize: The maximum size to set for the queue.
        """
        self._maxsize = maxsize

    def get_maxsize(self) -> int:
        """Gets the maximum size of the queue.

        This method returns the maximum number of items that the queue can hold. It is useful for determining
        capacity constraints of the queue in a specific scenario.

        Returns:
            int: The maximum size of the queue.
        """
        return self._maxsize

    # Get
    def get(
        self,
        block: bool = True,
        timeout: float | None = None,
        default: Any = search_sentinel,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Gets an item from the queue, waits for an item if the queue is empty.

        Args:
            block: Determines if this method will block execution.
            timeout: The time, in seconds, to wait for an item in the queue.

        Returns:
            The requested item.

        Raises:
            Empty: When there are no items to get in the queue when not blocking or on timing out.
            InterruptedError: When this method is interrupted by the interrupt event.
        """
        if self._closed:
            raise ValueError(f"Queue {self!r} is closed")

        interrupted = self.get_interrupt.is_set()
        res = None

        # Try to get an object without blocking.
        if not block:
            if self._rlock.acquire(block=False):
                try:
                    if self._poll():
                        res = self._recv_bytes()
                        self._sem.release()
                finally:
                    self._rlock.release()

        # Try to get an object without timing out.
        elif timeout is None:
            while not (interrupted := self.get_interrupt.is_set()):  # Walrus operator sets and evaluates.
                if self._rlock.acquire(block=False):
                    try:
                        if self._poll():
                            res = self._recv_bytes()
                            self._sem.release()
                            break
                    finally:
                        self._rlock.release()

        # Try to get an object and timing out when specified.
        else:
            deadline = perf_counter() + timeout
            while not (interrupted := self.get_interrupt.is_set()):  # Walrus operator sets and evaluates.
                if self._rlock.acquire(block=False):
                    try:
                        if self._poll():
                            res = self._recv_bytes()
                            self._sem.release()
                            break
                    finally:
                        self._rlock.release()
                if deadline is not None and deadline <= perf_counter():
                    break

        # Determine what to do.
        if interrupted:
            raise InterruptedError
        elif res is not None:
            return ForkingPickler.loads(res)  # Unserialize the data after having released the lock
        elif default is not search_sentinel:
            return default
        else:
            raise Empty

    async def get_async(
        self,
        block: bool = True,
        timeout: float | None = None,
        interval: float = 0.0,
        default: Any = search_sentinel,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Asynchronously gets an item from the queue, waits for an item if the queue is empty.

        Args:
            block: Determines if this method will block execution.
            timeout: The time, in seconds, to wait for an item in the queue.
            interval: The time, in seconds, between each queue check.

        Returns:
            The requested item.

        Raises:
            Empty: When there are no items to get in the queue when not blocking or on timing out.
            InterruptedError: When this method is interrupted by the interrupt event.
        """
        if self._closed:
            raise ValueError(f"Queue {self!r} is closed")

        interrupted = self.get_interrupt.is_set()
        res = None

        # Try to get an object without blocking.
        if not block:
            if self._rlock.acquire(block=False):
                try:
                    if self._poll():
                        res = self._recv_bytes()
                        self._sem.release()
                finally:
                    self._rlock.release()

        # Try to get an object without timing out.
        elif timeout is None:
            while not (interrupted := self.get_interrupt.is_set()):  # Walrus operator sets and evaluates.
                if self._rlock.acquire(block=False):
                    try:
                        if self._poll():
                            res = self._recv_bytes()
                            self._sem.release()
                            break
                    finally:
                        self._rlock.release()
                    await sleep(interval)

        # Try to get an object and timing out when specified.
        else:
            deadline = perf_counter() + timeout
            while not (interrupted := self.get_interrupt.is_set()):  # Walrus operator sets and evaluates.
                if self._rlock.acquire(block=False):
                    try:
                        if self._poll():
                            res = self._recv_bytes()
                            self._sem.release()
                            break
                    finally:
                        self._rlock.release()
                if deadline is not None and deadline <= perf_counter():
                    break
                await sleep(interval)

        # Determine what to do.
        if interrupted:
            raise InterruptedError
        elif res is not None:
            return ForkingPickler.loads(res)  # Unserialize the data after having released the lock
        elif default is not search_sentinel:
            return default
        else:
            raise Empty

    # Put
    def put(
        self,
        value: Any,
        block: bool | None = None,
        timeout: float | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Puts a value into the queue, waits for access to the queue.

        Args:
            value: The value to put into the queue.
            block: Determines if this method will block execution.
            timeout: The time, in seconds, to wait for space in the queue.

        Raises:
            Full: When there is no more space to put an item in the queue when not blocking or on timing out.
            InterruptedError: When this method is interrupted by the interrupt event.
        """
        if self._closed:
            raise ValueError(f"Queue {self!r} is closed")

        # Try to put a value without blocking.
        if not (block or (block is None and self.space_wait)):
            return super().put(value, block=False, timeout=timeout)
        # Try to put a value without timing out.
        elif timeout is None:
            while not self.put_interrupt.is_set():
                if self._sem.acquire(block=False):
                    with self._notempty:
                        if self._thread is None:
                            self._start_thread()
                        self._buffer.append(value)
                        self._notempty.notify()
                        return
        # Try to put a value and timing out when specified.
        else:
            deadline = perf_counter() + timeout
            while not self.put_interrupt.is_set():
                if self._sem.acquire(block=False):
                    with self._notempty:
                        if self._thread is None:
                            self._start_thread()
                        self._buffer.append(value)
                        self._notempty.notify()
                        return
                if deadline is not None and deadline <= perf_counter():
                    raise Full

        # Interruption leads to an error.
        raise InterruptedError

    async def put_async(
        self,
        value: Any,
        block: bool | None = None,
        timeout: float | None = None,
        interval: float = 0.0,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Asynchronously puts a value into the queue, waits for access to the queue.

        Args:
            value: The value to put into the queue.
            block: Determines if this method will block execution.
            timeout: The time, in seconds, to wait for space in the queue.
            interval: The time, in seconds, between each access check.

        Raises:
            Full: When there is no more space to put an item in the queue when not blocking or on timing out.
            InterruptedError: When this method is interrupted by the interrupt event.
        """
        # Try to put a value without blocking.
        if not (block or (block is None and self.space_wait)):
            return super().put(value, block=False, timeout=timeout)
        # Try to put a value without timing out.
        elif timeout is None:
            while not self.put_interrupt.is_set():
                if self._sem.acquire(block=False):
                    with self._notempty:
                        if self._thread is None:
                            self._start_thread()
                        self._buffer.append(value)
                        self._notempty.notify()
                        return

                await sleep(interval)
        # Try to put a value and timing out when specified.
        else:
            deadline = perf_counter() + timeout
            while not self.put_interrupt.is_set():
                if self._sem.acquire(block=False):
                    with self._notempty:
                        if self._thread is None:
                            self._start_thread()
                        self._buffer.append(value)
                        self._notempty.notify()
                        return
                if deadline is not None and deadline <= perf_counter():
                    raise Full

                await sleep(interval)

        # Interruption leads to an error.
        raise InterruptedError

    # Join
    def join(self) -> None:
        """Blocks until all items in the Queue have been gotten and the registry is updated."""
        while self.qsize() > 0:
            pass

    async def join_async(self, interval: float = 0.0) -> None:
        """Asynchronously, blockgroup until all items in the Queue have been gotten and the registry is updated.

        Args:
            interval: The time, in seconds, between each queue check.
        """
        while self.qsize() > 0:
            await sleep(interval)
