""" multiprocessingcontext.py.py

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
from ..context import BaseProcessContext, ProcessContext
from ..context import LockInterface, EventInterface, QueueInterface
from .synchronize import MultiProcessingLock, MultiProcessingEvent
from .queues import MultiProcessingQueue, MultiProcessingSimpleQueue


# Definitions #
# Classes #
class MultiProcessingContext(BaseProcessContext):
    """

    Class Attributes:

    Attributes:

    Args:

    """
    lock_type: type[LockInterface] = MultiProcessingLock
    event_type: type[EventInterface] = MultiProcessingEvent
    queue_type: type[QueueInterface] = MultiProcessingQueue
    simple_queue_type: type[QueueInterface] = MultiProcessingSimpleQueue


# Assignment #
ProcessContext.register["multiprocessing"] = MultiProcessingContext()
