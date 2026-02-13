"""__init__.py
Objects for managing shared memory.

"""

# Header #
__package_name__ = "blockobjects"

__author__ = "Anthony Fong"
__credits__ = ["Anthony Fong"]
__copyright__ = "Copyright 2022, Anthony Fong"
__license__ = "MIT"

__version__ = "0.1.0"


# Imports #
# Local Packages #
from .sharedmemoryregister import SharedMemoryRegister, PROCESS_SHARED_MEMORY_REGISTER
from .sharedmemory import SharedMemory
from .lockedsharedmemory import LockedSharedMemory

# Optional Modules #
try:
    import numpy
except ModuleNotFoundError:
    pass
else:
    from .sharedarray import *
