""" basecontextualobject.py.py
A base class for an object containing a context object which determines its implementation.
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
from typing import Any

# Third-Party Packages #

# Local Packages #
from ...interfaces import ContextualObjectInterface
from .baseprocessingcontext import BaseProcessingContext


# Definitions #
# Classes #
class BaseContextualObject(ContextualObjectInterface):
    """A base class for an object containing a context object which determines its implementation.

    Attributes:
        _context: The context of this object.

    Args:
        *args: Variable length argument list for the parent.
        context: The context to assign this object to.
        init: Determines if this object will construct.
        **kwargs: Arbitrary keyword arguments for the parent.
    """

    # Attributes #
    _context: BaseProcessingContext | None = None

    # Properties #
    @property
    def context(self) -> BaseProcessingContext:
        """The context of this object."""
        return self.get_context()

    @context.setter
    def context(self, value: BaseProcessingContext) -> None:
        self.set_context(value)

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        *args: Any,
        context: BaseProcessingContext | None = None,
        init: bool = True,
        **kwargs: Any,
    ) -> None:
        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct(*args, context=context, **kwargs)

    # Instance Methods #
    # Constructors/Destructors
    def construct(self, *args: Any, context: BaseProcessingContext | None = None, **kwargs: Any) -> None:
        """Constructs this object.

        Args:
            *args: Variable length argument list for the parent constructor.
            context: The context to assign this object to.
            **kwargs: Arbitrary keyword arguments for the parent constructor.
        """
        if context is not None:
            self._context = context

        super().construct(*args, **kwargs)

    # Context
    def get_context(self) -> BaseProcessingContext:
        """Gets the context of this object.

        Returns:
            The context of this object.
        """
        return self._context

    def set_context(self, context: BaseProcessingContext) -> None:
        """Sets the context of this object to the given context.

        Args:
            context: The context to assign this object to.
        """
        self._context = context
