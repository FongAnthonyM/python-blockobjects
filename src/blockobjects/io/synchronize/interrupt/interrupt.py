""" multiprocessinginterrupt.py
An MultiProcessingEvent which intended to act interrupt.
"""
# Package Header #
from ....header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Standard Libraries #

# Third-Party Packages #

# Local Packages #
from ....process.context import BaseProcessContext
from ..event import Event


# Definitions #
# Classes #
class Interrupt(Event):
    """An Event which is intended to act as an interrupt.

    Attributes:
        parent: An ContextualEvent which, if set, will also set this interrupt.

    Args:
        parent: An ContextualEvent which, if set, will also set this interrupt.
        ctx: The context for the Python multiprocessing.
    """

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, parent: Event | None = None, *, context: BaseProcessContext | None = None, init: bool = True) -> None:
        # New Attributes #
        self.parent: Event | None = parent

        # Construction #
        super().__init__(context=context)

    # Instance Methods #
    def is_set(self) -> bool:
        """Checks if this interrupt or its parent has been set.

        Returns:
            If this interrupt or its parent has been set.
        """
        if self.parent is not None and self.parent.is_set():
            self.set()
        return super().is_set()
