""" arrayreducer.py
Extends SharedMemory with a reference count and optional registration for unlinking when the process dies.
"""
# Package Header #
from ....header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Standard Libraries #
from collections import deque
from contextlib import contextmanager
from functools import partial
from multiprocessing.shared_memory import SharedMemory
from multiprocessing.reduction import ForkingPickler
from typing import Any, TypeVar

# Third-Party Packages #
from baseobjects import BaseObject
from numpy import ndarray

# Local Packages #
from .sharedarray import SharedArray


# Definitions #
# Classes #
class ArrayReducer(BaseObject):
    # Attributes #
    shared_memory_type: type[SharedMemory] = SharedMemory
    shared_array_type: type[SharedArray] = SharedArray
    shared_memories: dict[int, deque[SharedMemory]]
    current_shared_memories: deque[SharedMemory] | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # New Attributes #
        self.shared_memories = {}

        # Parent Attributes #
        super().__init__(*args, **kwargs)

    @contextmanager
    def persist(self) -> None:
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

    def reduce_array(self, array: ndarray) -> tuple[type, tuple[Any, ...]]:
        # Create Shared Memory
        sm = self.shared_memory_type(create=True, size=int(array.nbytes))

        # Create Array with Shared Memory
        sm_array = ndarray(array.shape, dtype=array.dtype, buffer=sm.buf)

        # Copy Data into Shared Memory
        sm_array[:] = array[:]

        # Add Shared Memory to Current Shared Memories
        if self.current_shared_memories is not None:
            self.current_shared_memories.append(sm)

        # Return Reduction Tuple
        func = partial(self.rebuild_array, self.shared_array_type)
        args = (None, array.shape, sm.name, array.dtype, 0, None, None)
        return func, args

    @staticmethod
    def rebuild_array(cls: type[SharedArray], *args, **kwargs) -> ndarray:
        # Consider How to make this more efficient
        shared_array = cls(*args, **kwargs)
        array = shared_array.copy_array()
        shared_array.close()
        shared_array.unlink()
        return array


# Registration #
DEFAULT_ARRAY_REDUCER = ArrayReducer()
ForkingPickler.register(ndarray, DEFAULT_ARRAY_REDUCER.reduce_array)
