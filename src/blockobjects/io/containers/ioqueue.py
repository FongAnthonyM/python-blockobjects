""" ioqueue.py
IOQueue stores values within it using a queue. It mixes in ContextualQueue to give it dynamic implementation where its
implementation depend on which multiprocessing context it is assigned to, giving it the flexibility to be used with
several multiprocessing frameworks. Additionally, the context can be changed at any time.
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
from ...process import ContextualQueue
from ..base import BaseIO


# Definitions #
# Classes #
class IOQueue(ContextualQueue, BaseIO):
    """An IO object which stores values within it using a queue.

    IOQueue mixes in ContextualQueue to give it dynamic implementation where its implementation depend on which
    multiprocessing context it is assigned to, giving it the flexibility to be used with several multiprocessing
    frameworks. Additionally, the context can be changed at any time.
    """
