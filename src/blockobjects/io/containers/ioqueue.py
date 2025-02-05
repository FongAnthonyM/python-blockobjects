""" ioqueue.py
IOQueue stores values within it using a queue.
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

# Third-Party Packages #

# Local Packages #
from ...process import AsyncQueue
from ..base import BaseIO


# Definitions #
# Classes #
class IOQueue(AsyncQueue, BaseIO):
    """An IO object which stores values within it using a queue."""
