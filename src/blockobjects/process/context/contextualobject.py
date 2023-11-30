""" contextualobject.py.py

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
from baseobjects import BaseObject

# Local Packages #
from .baseprocesscontext import BaseProcessContext


# Definitions #
# Classes #
class ContextualObject(BaseObject):
    """

    Class Attributes:

    Attributes:

    Args:

    """
    default_context: BaseProcessContext | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, *, context: BaseProcessContext | None = None, init: bool = True) -> None:
        # New Attributes #
        self._context: BaseProcessContext | None = self.default_context

        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct(context=context)

    @property
    def context(self) -> BaseProcessContext:
        return self._context

    @context.setter
    def context(self, value: BaseProcessContext) -> None:
        self.set_context(value)

    # Instance Methods #
    # Constructors/Destructors
    def construct(self, *, context: BaseProcessContext | None = None) -> None:
        if context is not None:
            self._context = context

        super().construct()

    # Context
    def set_context(self, context: BaseProcessContext) -> None:
        self._context = context
