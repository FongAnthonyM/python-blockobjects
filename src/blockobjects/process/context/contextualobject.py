""" contextualobject.py.py
A base class for an object containing a context object which determines its implementation.
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
from .baseprocessingcontext import BaseProcessingContext


# Definitions #
# Classes #
class ContextualObject(BaseObject):
    """A base class for an object containing a context object which determines its implementation.

    Attributes:
        _context: The context of this object.

    Args:
        context: The context to assign this object to.
        init: Determines if this object will construct.
    """
    # Attributes #
    _context: BaseProcessingContext | None = None

    # Properties #
    @property
    def context(self) -> BaseProcessingContext:
        """The context of this object."""
        return self._context

    @context.setter
    def context(self, value: BaseProcessingContext) -> None:
        self.set_context(value)

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, *, context: BaseProcessingContext | None = None, init: bool = True) -> None:
        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct(context=context)

    # Instance Methods #
    # Constructors/Destructors
    def construct(self, *, context: BaseProcessingContext | None = None) -> None:
        """Constructs this object.

        Args:
            context: The context of this object.
        """
        if context is not None:
            self._context = context

        super().construct()

    # Context
    def set_context(self, context: BaseProcessingContext) -> None:
        """Sets the context of this object to the given context.

        Args:
            context: The context to assign this object to.
        """
        self._context = context
