""" iomanager.py
An IO object which maps named inputs to names outputs in a one-to-one manner.
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
from collections.abc import Iterable
from typing import Any

# Third-Party Packages #
from baseobjects import BaseDict

# Local Packages #
from .baseio import IOMap, BaseIO
from .baseiomultiplexer import BaseIOMultiplexer
from .iocontainer import IOContainer


# Definitions #
# Classes #
class IOManager(BaseDict, BaseIOMultiplexer):
    """An IO object which maps named inputs to names outputs in a one-to-one manner.

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
            io_: The input/outputs to be managed
            *args: Arguments for inheritance.
            **kwargs: Keyword arguments for inheritance.
        """
        if io_ is not None:
            self.update_io(io_)

        super().construct(*args, **kwargs)

    # Mapping
    def update_io(self, __m: Any = {}, /, **kwargs) -> None:
        """Updates this object's items. Nones are replaced with the default IO type.

        Args:
            __m: A mapping with IO objects which will replace items in this manager.
            **kwargs: IO objects which will replace items in this manager.
        """
        items = (kwargs if __m is None else (__m | kwargs))
        self.update({k: (self.default_io() if v is None else v) for k, v in items.items()})

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
        if type_ is None:
            type_ = self.default_io

        if isinstance(name, str):
            name = (name,)

        for n in name:
            self.data[n] = type_(*args, **kwargs)

    # Get
    def get_item(self, name: str, **kwargs: Any) -> Any:
        """Gets a value from this IO object.

        Args:
            name: The names of the items to get from this IO object.

        Returns:
            The all items.
        """
        return self.data[name].get(name=name, **kwargs)

    def get_items(self, names: Iterable[str, ...], **kwargs: Any) -> Any:
        """Gets multiple values from this IO object.

        Args:
            names: The names of the items to get from this IO object.

        Returns:
            The all items.
        """
        return tuple(self.data[name].get(name=name, **kwargs) for name in names)

    def get_all(self, *args, **kwargs) -> dict[str, Any]:
        """Gets all items from the IO object.

        Args:
            *args: The arguments to use to get from the contained objects.
            **kwargs: The keyword arguments to use to get from the contained objects.

        Returns:
            The all items in the IO objects.
        """
        return {k: v.get(*args, **kwargs) for k, v in self.data.items()}

    # Put
    def put_item(self, name: str, value: dict[str, Any]) -> None:
        """Put an item into an IO object.

        Args:
            name: The key name to the IO object to put the item into.
            value: The keyword arguments of the put of the IO object.
        """
        self.data[name].put(**value)

    def put_all(self, __m: Any = None, /, **kwargs: Any) -> None:
        """Puts all given keyword IO values into their IO objects.

        Args:
            __m: A mapping with the IO values to put into IO objects.
            **kwargs: The IO values to put into IO objects.
        """
        for k, v in (kwargs if __m is None else (__m | kwargs)).items():
            self.data[k].put(v)

    # IO Mapping
    def get_links(self) -> dict[str, IOMap] | None:
        """Gets the links of this IO object.

       Returns:
           The links of this IO object.
       """
        return {n: m.generate_io_map() for n, m in self.data}
