"""asynccontext.py
Summary.

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
from ...interfaces import LockInterface, EventInterface, QueueInterface, ProxyInterface
from ..bases import BaseProcessingContext
from ..managercontext import ManagerContext
from .synchronize import AsyncLock, AsyncEvent
from .queues import AsyncQueue
# from .proxies import AsyncProxy  # Todo: Implement this someday


# Definitions #
# Classes #
class AsyncContext(BaseProcessingContext):
    """A ProcessContext for python's multiprocessing library.

    Attributes:
        lock_type: The type of lock to create when creating locks.
        event_type: The type of event to create when creating events.
        queue_type: The type of queue to create when creating queues.
        simple_queue_type: The type of simple queue to create when creating simple queues.
    """

    # Attributes #
    lock_type: type[LockInterface] = AsyncLock
    event_type: type[EventInterface] = AsyncEvent
    queue_type: type[QueueInterface] = AsyncQueue
    simple_queue_type: type[QueueInterface] = AsyncQueue
    # proxy_type: type[ProxyInterface] = AsyncProxy


# Assignment #
ManagerContext.contexts["async"] = AsyncContext()
