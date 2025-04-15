""" ioqueue.py
IOQueue stores values within it using a queue.
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

# Third-Party Packages #

# Local Packages #
from ...process import AsyncQueue
from ..base import BaseIO


# Definitions #
# Classes #
class IOQueue(AsyncQueue, BaseIO):
    """An IO object which stores values within it using a queue."""
