""" iorouter.py
An IO object which maps inputs to outputs.
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
from typing import Any

# Third-Party Packages #
from baseobjects.collections import OrderableDict

# Local Packages #
from .baseio import IOMap, BaseIO
from .baseiomultiplexer import BaseIOMultiplexer
from .iocontainer import IOContainer


# Definitions #
# Classes #
class IORouter(OrderableDict, BaseIOMultiplexer):
    """An IO object which maps inputs to outputs.

    The default functionality is put a single output into multiple inputs.

    Class Attributes:
        default_get: The default name of the method to use for getting.
        default_put: The default name of the method to use for putting.
        default_io: The default IO object type to populate this object when constructed.

    Attributes:
        get: The method multiplexer which manages which get method to run when called.
        put: The method multiplexer which manages which get method to run when called.

    Args:
        io_: The input/outputs to be managed.
        *args: Arguments for inheritance.
        init: Determines if this object will construct.
        **kwargs: Keyword arguments for inheritance.
    """
    default_get: str | None = "get_all"
    default_put: str | None = "put_all"
    default_io: type[BaseIO] = IOContainer

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        io_: dict[str, BaseIO | None] | None = None,
        *args: Any,
        init: bool = True,
        **kwargs: Any,
    ) -> None:
        # Parent Attributes #
        super().__init__(*args, **kwargs)

        # Construction #
        if init:
            self.construct(io_=io_, *args, **kwargs)

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        io_: dict[str, BaseIO | None] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Constructs this object.

        Args:
            io_: The input/outputs to be managed.
            *args: Arguments for inheritance.
            **kwargs: Keyword arguments for inheritance.
        """
        if io_ is not None:
            self.update_io(io_)

        super().construct(*args, **kwargs)

    # Mapping
    def update_io(self, __m: Any = {}, /, **kwargs) -> None:
        """Updates this object's items. Nones are replaced with the default io type.

        Args:
            __m: A mapping with io objects which will replace items in this manager.
            **kwargs: Io objects which will replace items in this manager.
        """
        items = (kwargs if __m is None else (__m | kwargs))
        self.update({k: (self.default_io() if v is None else v) for k, v in items.items()})

    # Get
    def get_item(self, name: str, **kwargs: Any) -> Any:
        """Gets a value from an io object.

        Returns:
            The all items.
        """
        return self.data[name].get(name=name, **kwargs)

    def get_all(self, *args, **kwargs) -> dict[str, Any]:
        """Gets all items from the io object.

        Returns:
            The all items in the io objects.
        """
        return {k: v.get(*args, **kwargs) for k, v in self.data.items()}

    # Put
    def put_item(self, name: str, value: dict[str, Any]) -> None:
        """Put an item into an io object.

        Args:
            name: The key name to the io object to put the item into.
            value: The keyword arguments of the put of the io object.
        """
        self.data[name].put(**value)

    def put_all(self, *args, **kwargs: Any) -> None:
        """Puts all given keyword io values into their io objects.

        Args:
            *args: The arguments for the inner io object's put.
            **kwargs: The keyword arguments for the inner io object's put.
        """
        for io_object in self.data.values():
            io_object.put(*args, **kwargs)

    # IO Mapping
    def get_links(self) -> dict[str, IOMap] | None:
        """Gets the links of this IO object.

       Returns:
           The links of this IO object.
       """
        return {n: m.generate_io_map() for n, m in self.data}

