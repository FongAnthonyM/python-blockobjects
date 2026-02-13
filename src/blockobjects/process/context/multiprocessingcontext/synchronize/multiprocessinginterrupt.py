"""multiprocessinginterrupt.py
An MultiProcessingEvent which intended to act interrupt.

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
from multiprocessing.synchronize import Event
from multiprocessing.context import BaseContext

# Third-Party Packages #

# Local Packages #
from .multiprocessingevent import MultiProcessingEvent


# Definitions #
# Classes #
class MultiProcessingInterrupt(MultiProcessingEvent):
    """An MultiProcessingEvent which intended to act interrupt.

    Attributes:
        parent: An Event which, if set, will also set this interrupt.

    Args:
        parent: An Event which, if set, will also set this interrupt.
        ctx: The context for the Python multiprocessing.
    """
    # Attributes #
    parent: Event | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, parent: Event | None = None, *, ctx: BaseContext | None = None) -> None:
        # Attributes #
        self.parent = parent

        # Construction #
        super().__init__(ctx=ctx)

    # Instance Methods #
    def is_set(self) -> bool:
        """Checks if this interrupt or its parent has been set.

        Returns:
            If this interrupt or its parent has been set.
        """
        if self.parent is not None and self.parent.is_set():
            self.set()
        return super().is_set()

    async def is_set_async(self) -> bool:
        """Asynchronously checks if the event is set.

        Returns:
            True if the event is set, otherwise False.
        """
        if self.parent is not None and self.parent.is_set():
            self.set()
        return await super().is_set_async()
