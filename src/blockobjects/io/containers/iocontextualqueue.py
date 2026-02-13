"""iocontextualqueue.py
IOContextualQueue stores values within it using a queue. It mixes in ContextualQueue to give it dynamic implementation where its.

implementation depend on which multiprocessing context it is assigned to, giving it the flexibility to be used with
several multiprocessing frameworks. Additionally, the context can be changed at any time.
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
from ...process import ContextualQueue
from ..base import BaseIO


# Definitions #
# Classes #
class IOContextualQueue(ContextualQueue, BaseIO):
    """An IO object which stores values within it using a queue.

    IOContextualQueue mixes in ContextualQueue to give it dynamic implementation where its implementation depend on which
    multiprocessing context it is assigned to, giving it the flexibility to be used with several multiprocessing
    frameworks. Additionally, the context can be changed at any time.
    """
