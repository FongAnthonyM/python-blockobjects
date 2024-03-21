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
from typing import ClassVar, Any

# Third-Party Packages #
from baseobjects import BaseDict

# Local Packages #
from .baseio import IOMap, BaseIO
from .baseiomultiplexer import BaseIOMultiplexer
from .iocontainer import IOContainer
from .iodelegator import IODelegator


# Definitions #
# Classes #
class IOManager(BaseDict, BaseIOMultiplexer):
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
    # Class Attributes #
    default_get: ClassVar[str | None] = "get_all"
    default_put: ClassVar[str | None] = "put_all"

    # Attributes #
    default_io: type[BaseIO] = IOContainer
    order: list[str, ...]

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
        self.order = []

        # Parent Attributes #
        super().__init__(*args, **kwargs)

        # Construction #
        if init:
            self.construct(io_, names, *args, **kwargs)

    # Set Item
    def __setitem__(self, key: str, item: BaseIO) -> None:
        """Sets an IO within this manager. If an existing IO is an IODelegator, set it to

        Args:
            key: The name of the IO to set.
            item: The IO object to set.
        """
        if (io_object := self.data.get(key, None)) is not None and isinstance(io_object, IODelegator):
            io_object.io = item
        else:
            self.data[key] = item

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        io_: dict[str, BaseIO | None] | None = None,
        names: Iterable[str] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Constructs this object.

        Args:
            io_: The input/outputs to be managed.
            names: The names of IO to create and manage.
            *args: Arguments for inheritance.
            **kwargs: Keyword arguments for inheritance.
        """
        if names is not None:
            self.create_io(name=names)

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
            if n not in self.data:
                self.order.append(name)
            self.data[n] = type_(*args, **kwargs)

    # Ordering
    def ordered_to_dict(self, ordered: Iterable[Any]) -> dict[str, Any]:
        """Creates a dictionary from an ordered iterable based on the order of this IO.

        Args:
            ordered: The ordered iterable to create a dictionary from.

        Returns:
            The dictionary of the ordered items.
        """
        return dict(zip(self.order, ordered))

    def dict_to_ordered(self, dict_: dict[str, Any]) -> tuple[Any, ...]:
        """Creates an ordered tuple from dictionary based on the order of this IO.

        Args:
            dict_: The dictionary to create an ordered tuple from.

        Returns:
            The tuple of the ordered items.
        """
        return tuple(dict_.get(name) for name in self.order)

    # Get
    def get_item(self, name: str, **kwargs: Any) -> Any:
        """Gets an item from the requested IO object.

        Args:
            name: The name of tje IO object to get an item from.
            **kwargs: The keyword arguments for getting the item from the requested IO object.

        Returns:
            The requested item.
        """
        return self.data[name].get(name=name, **kwargs)

    def get_items(self, names: Iterable[str, ...], **kwargs: Any) -> tuple[Any, ...]:
        """Gets items from multiple IO objects.

        Args:
            names: The names of the IO objects to get items from.
            **kwargs: The keyword arguments for getting items from the requested IO objects.

        Returns:
            The requested items.
        """
        return tuple(self.data[name].get(name=name, **kwargs) for name in names)

    def get_ordered(self, **kwargs: Any) -> tuple[Any, ...]:
        """Gets items from all IO objects in order.

        Args:
            **kwargs: The keyword arguments for getting items from the requested IO objects.

        Returns:
            Items from all IO objects in order.
        """
        return tuple(self.data[name].get(name=name, **kwargs) for name in self.order)

    def get_all(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        """Gets items from all IO objects organized in a dictionary.

        Args:
            *args: The arguments for getting items from the requested IO objects.
            **kwargs: The keyword arguments for getting items from the requested IO objects.

        Returns:
            Items from all IO objects organized in a dictionary.
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

    def put_ordered(self, values: Iterable[Any]) -> None:
        """Puts given values into their IO objects based on this object's order.

        Args:
            values: The items to put.
        """
        for k, v in zip(self.order, values):
            self.data[k].put(v)

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
