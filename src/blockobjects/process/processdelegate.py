""" processdelegate.py.py

"""
# Package Header #
from ..header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Standard Libraries #

# Third-Party Packages #


# Local Packages #
from .context import BaseProcessContext, ContextualObject


# Definitions #
# Classes #
class ProcessDelegate(ContextualObject):
    """

    Class Attributes:

    Attributes:

    Args:

    """
    # Magic Methods #
    # Construction/Destruction
    def __init__(self, *, context: BaseProcessContext | None = None, init: bool = True) -> None:
        # New Attributes #
        self.remote_process = None

        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct(context=context)

    # Instance Methods #
    # Constructors/Destructors
    def construct(self, *, context: BaseProcessContext | None = None) -> None:
        super().construct(context=context)

    # Context
    def set_context(self, context: BaseProcessContext) -> None:
        super().set_context(context=context)

    # Remote
    def is_remote(self) -> bool:
        pass

    def create_remote_process(self):
        self.remote_process = self.context.create_remote_process(self)


