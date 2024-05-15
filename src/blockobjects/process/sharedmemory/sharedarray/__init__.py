""" __init__.py
Objects for managing shared memory for numpy arrays.
"""
# Package Header #
from ....header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Local Packages #
from .sharedarray import SharedArray
from .lockedsharedarray import LockedSharedArray
from .arrayreducer import ArrayReducer, DEFAULT_ARRAY_REDUCER
