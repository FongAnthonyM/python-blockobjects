""" delegatingiomanager.py
An IO object which maps named inputs to names outputs in a one-to-one manner.
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
from collections.abc import Iterable, Callable
from typing import ClassVar, Any

# Third-Party Packages #
from ...process import BaseProcessingContext, AsyncContext, ManagerContext, DEFAULT_PROCESS_CONTEXT

# Local Packages #
from ..base import IOMap, BaseIO, BaseIOMultiplexer, IODelegator, IOWrapper
from ..containers import IOQueue
from .baseiomanager import BaseIOManager


# Definitions #
# Classes #
class ContextualIOManager(BaseIOManager):
    """An IO object which maps named inputs to names outputs in a one-to-one manner.

    Class Attributes:
        default_get: The default name of the method to use for getting.
        default_put: The default name of the method to use for putting.

    Attributes:
        get: The method multiplexer which manages which get method to run when called.
        put: The method multiplexer which manages which get method to run when called.
        default_io: The default IO object type to populate this object when constructed.

    Args:
        io_: The input/outputs to be managed.
        *args: Arguments for inheritance.
        init: Determines if this object will construct.
        **kwargs: Keyword arguments for inheritance.
    """

    # Attributes #
    default_context: str = "local"
    contexts: dict[str, BaseProcessingContext] = {
        "default": DEFAULT_PROCESS_CONTEXT,
        "local": ManagerContext({"async": AsyncContext()}, "async"),
    }

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        io_: dict[str, BaseIO | None] | None = None,
        names: Iterable[str] | None = None,
        *args: Any,
        init: bool = True,
        **kwargs: Any,
    ) -> None:
        # Attributes #
        self.contexts = self.contexts.copy()

        # Parent Attributes #
        super().__init__(init=False)

        # Construction #
        if init:
            self.construct(io_, names, *args, **kwargs)

    # Context
    def set_all_contexts(self, context: BaseProcessingContext | None) -> None:
        """Sets all contained objects to a given context.

        Args:
            context: The context to set the objects to.
        """
        for io_ in self.data.values():
            if (set_context := getattr(io_, 'set_context', None)) is not None:
                set_context(context)

    # IO Objects
    def create_io(
        self,
        name: str | Iterable[str],
        type_: type[BaseIO] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Creates a new named IO object or new IO objects from a list of names.

        Args:
            name: The key name of the IO to create.
            type_: The type of IO to create.
            *args: The arguments for constructing the new IO object.
            **kwargs: The keyword arguments for constructing the new IO object.
        """
        kwargs = {"context": self.contexts[self.default_context]} | (kwargs or {})
        super().create_io(name, type_, *args, **kwargs)
