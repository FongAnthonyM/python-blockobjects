""" iosimplequeue.py
An IO object which stores values within it using a simple queue
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

from ...process import ContextualSimpleQueue
from ..base import BaseIO


# Definitions #
# Classes #
class IOSimpleQueue(ContextualSimpleQueue, BaseIO):
    """An IO object which stores values within it using a simple queue."""
