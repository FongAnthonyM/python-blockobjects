"""arrayreducer.py
Reduces numpy arrays to shared memory.

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
from collections import deque
from collections.abc import Iterable
from contextlib import contextmanager
import os
from multiprocessing.shared_memory import SharedMemory
from multiprocessing.reduction import ForkingPickler
from typing import Any, Callable

# Third-Party Packages #
from baseobjects import BaseObject
from numpy import ndarray

# Local Packages #


# Definitions #
# Classes #
class ArrayReducer(BaseObject):
    """Reduces numpy arrays to shared memory.

    This reduction is intended to improve performance when passing numpy arrays between processes, and is primarily for
    multiprocessing.

    Attributes:
        shared_memory_type: The type of the shared memory to be used for reduction.
        shared_memories (dict[int, deque[SharedMemory]]): A dictionary storing all active shared memory objects,
            mapped by their unique identifiers.
        current_shared_memories (deque[SharedMemory] | None): The current active set of shared memory objects
            being managed within a specific persisted scope.
    """
    # Attributes #
    shared_memory_type: type[SharedMemory] = SharedMemory
    shared_memories: dict[int, deque[SharedMemory]]
    current_shared_memories: deque[SharedMemory] | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # New Attributes #
        self.current_shared_memories = shared_memories = deque()
        self.shared_memories = {id(shared_memories): shared_memories}

        # Parent Attributes #
        super().__init__(*args, **kwargs)

    def clear_current_memories(self) -> None:
        """Clears the current shared memory objects."""
        for shared_memory in self.current_shared_memories:
            shared_memory.close()
            shared_memory.unlink()
        self.current_shared_memories.clear()

    def clear_all_memories(self) -> None:
        """Clears all shared memory objects."""
        for shared_memories in self.shared_memories.values():
            for shared_memory in shared_memories:
                shared_memory.close()
                shared_memory.unlink()
        self.shared_memories.clear()

    @contextmanager
    def persist(self) -> None:
        """Manages a context for creating and releasing shared memory storage.

        This method implements a context manager to temporarily store shared memories within a storage location. Upon
        entering the context, a new shared memory container is created for storing shared memories, and it replaces the
        current active shared memory container. On exiting the context, the temporary shared memories are released and
        the previous active storage is restored.

        Yields:
            None: This context manager does not return any value while in context.
        """
        # Create New Shared Memories Storage Location
        previous_memories = self.current_shared_memories
        self.current_shared_memories = shared_memories = deque()
        memories_id = id(shared_memories)
        self.shared_memories[memories_id] = shared_memories
        yield

        # Release Shared Memories from Storage
        del self.shared_memories[memories_id]
        self.current_shared_memories = previous_memories
        for shared_memory in shared_memories:
            shared_memory.close()

    def reduce_array_win(self, array: ndarray) -> tuple[Callable, tuple[Any, ...]]:
        """Reduces a NumPy array into a tuple containing a callable rebuild function and its respective arguments.

        A NumPy array is reduces by copying its contents in shared memory. This allows efficient sharing of large arrays
        across processes without copying the data multiple times.

        Args:
            array (ndarray): The input NumPy array to be reduced.

        Returns:
            tuple[callable, tuple]: A tuple where the first element is a callable function to recreate the array
            from shared memory, and the second element is a tuple of arguments required by the function.

        """
        # Create Shared Memory
        if (b_size := int(array.nbytes)) != 0:
            sm = self.shared_memory_type(create=True, size=b_size)
            sm_name = sm.name

            # Create Array with Shared Memory
            sm_array = ndarray(array.shape, dtype=array.dtype, buffer=sm.buf)

            # Copy Data into Shared Memory
            sm_array[:] = array[:]

            # Add Shared Memory to memory resister so it does not get deleted before it is rebuilt
            if self.current_shared_memories is not None:
                self.current_shared_memories.append(sm)
        else:
            sm_name = None

        # Return Reduction Tuple
        func = self.rebuild_array
        args = (self.shared_memory_type, sm_name, array.shape, array.dtype)
        return func, args

    def reduce_array_posix(self, array: ndarray) -> tuple[Callable, tuple[Any, ...]]:
        """Reduces a NumPy array into a tuple containing a callable rebuild function and its respective arguments.

        A NumPy array is reduces by copying its contents in shared memory. This allows efficient sharing of large arrays
        across processes without copying the data multiple times.

        Args:
            array (ndarray): The input NumPy array to be reduced.

        Returns:
            tuple[callable, tuple]: A tuple where the first element is a callable function to recreate the array
            from shared memory, and the second element is a tuple of arguments required by the function.

        """
        # Create Shared Memory
        if (b_size := int(array.nbytes)) != 0:
            sm = self.shared_memory_type(create=True, size=b_size)
            sm_name = sm.name

            # Create Array with Shared Memory
            sm_array = ndarray(array.shape, dtype=array.dtype, buffer=sm.buf)

            # Copy Data into Shared Memory
            sm_array[:] = array[:]
        else:
            sm_name = None

        # Return Reduction Tuple
        func = self.rebuild_array
        args = (self.shared_memory_type, sm_name, array.shape, array.dtype)
        return func, args

    @staticmethod
    def rebuild_array(shared_memory_type: type[SharedMemory], name: str | None, shape: Iterable, dtype: Any) -> ndarray:
        """Reconstructs a numpy array from shared memory.

        This method retrieves a shared memory block, reconstructs a numpy array using the provided shape and datatype,
        and returns a copy of the array. After copying the data, the shared memory block is closed and unlinked to
        free resources.

        Args:
            shared_memory_type: A type representing the shared memory to be accessed.
            name: The unique name of the shared memory block to be used.
            shape: An iterable representing the shape of the numpy array.
            dtype: The data type of the numpy array.

        Returns:
            ndarray: A new numpy array constructed from the shared memory contents.
        """
        if name is None:
            return ndarray(shape=shape, dtype=dtype)
        else:
            shared_memory = shared_memory_type(name=name)
            _array = ndarray(shape=shape, dtype=dtype, buffer=shared_memory.buf)
            array = _array.copy()
            shared_memory.close()
            shared_memory.unlink()
            return array


# Registration #
DEFAULT_ARRAY_REDUCER = ArrayReducer()
if os.name == "nt":
    ForkingPickler.register(ndarray, DEFAULT_ARRAY_REDUCER.reduce_array_win)
else:
    ForkingPickler.register(ndarray, DEFAULT_ARRAY_REDUCER.reduce_array_posix)
