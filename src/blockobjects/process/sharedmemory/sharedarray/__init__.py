""" __init__.py
Objects for managing shared memory for numpy arrays.
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
from .sharedarray import SharedArray
from .lockedsharedarray import LockedSharedArray
from .arrayreducer import ArrayReducer, DEFAULT_ARRAY_REDUCER
