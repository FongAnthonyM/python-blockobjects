""" arbitratingiomanager.py
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
from ..base import IOMap, BaseIO, BaseIOMultiplexer, IOForwarder, IOWrapper
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
    default_io_type: type[BaseIO] = IOQueue

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
        for io_ in self.io_objects.values():
            if (set_context := getattr(io_, 'set_context', None)) is not None:
                set_context(context)

    # IO Objects
    def create_io(
        self,
        name: str | int,
        group: str = "__default__",
        type_: type[BaseIO] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> BaseIO:
        """Creates a new named IO object.

        Args:
            name: The key name of the IO to create.
            group: The group which the new IO will be under.
            type_: The type of IO to create.
            *args: Positional arguments for constructing the new IO object.
            **kwargs: Keyword arguments for constructing the new IO object.
        """
        kwargs = {"context": self.contexts[self.default_context]} | (kwargs or {})
        return super().create_io(name, group, type_, *args, **kwargs)

    def create_ios(
        self,
        names: Iterable[str | int] | None,
        group: str = "__default__",
        groups: dict[str, Iterable[str | int]] | None = None,
        type_: type[BaseIO] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, dict[str | int, BaseIO]]:
        """Creates a new named IO object or new IO objects from a list of names.

        Args:
            names: The key names of the IOs to create.
            group: The group name which the new IOs will be under.
            groups: Groups which create new IOs under with their names.
            type_: The type of IO to create.
            *args: Positional arguments for constructing the new IO object.
            **kwargs: Keyword arguments for constructing the new IO object.
        """
        kwargs = {"context": self.contexts[self.default_context]} | (kwargs or {})
        return super().create_ios(names, group, groups, type_, *args, **kwargs)
