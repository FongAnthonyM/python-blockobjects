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
from weakref import ref

# Third-Party Packages #

# Local Packages #
from ..context import BaseProcessingContext, ManagerContext
from ..context import LockInterface, EventInterface, QueueInterface, ProxyInterface
from .synchronize import MultiProcessingLock, MultiProcessingEvent
from .queues import MultiProcessingQueue, MultiProcessingSimpleQueue
from .multiprocessingexecutor import MultiProcessingProxy


# Definitions #
# Classes #
class MultiProcessingContext(BaseProcessingContext):
    """A ProcessContext for python's multiprocessing library.

    Attributes:
        lock_type: The type of lock to create when creating locks.
        event_type: The type of event to create when creating events.
        queue_type: The type of queue to create when creating queues.
        simple_queue_type: The type of simple queue to create when creating simple queues.
    """
    # Attributes #
    lock_type: type[LockInterface] = MultiProcessingLock
    event_type: type[EventInterface] = MultiProcessingEvent
    queue_type: type[QueueInterface] = MultiProcessingQueue
    simple_queue_type: type[QueueInterface] = MultiProcessingSimpleQueue
    proxy_type: type[ProxyInterface] = MultiProcessingProxy


# Assignment #
ManagerContext.contexts["multiprocessing"] = MultiProcessingContext()
