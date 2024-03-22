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
from asyncio import gather
from collections.abc import Iterable
from typing import ClassVar, Any

# Third-Party Packages #
from baseobjects.collections import OrderableDict

# Local Packages #
from .base import IOMap, BaseIO, BaseIOMultiplexer, IODelegator
from .containers import IOQueue


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

    # Class Attributes #
    default_get: ClassVar[str] = "get_all"
    default_get_async: ClassVar[str] = "get_all_async"
    default_put: ClassVar[str] = "put_to_all"
    default_put_async: ClassVar[str] = "put_to_all_async"

    # Attributes #
    default_io: type[BaseIO] = IOQueue

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
        """Updates this object's items. Nones are replaced with the default io type.

        Args:
            __m: A mapping with io objects which will replace items in this manager.
            **kwargs: Io objects which will replace items in this manager.
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

    async def get_item_async(self, name: str, **kwargs: Any) -> Any:
        """Asynchronously gets an item from the requested IO object.

        Args:
            name: The name of tje IO object to get an item from.
            **kwargs: The keyword arguments for getting the item from the requested IO object.

        Returns:
            The requested item.
        """
        return await self.data[name].get_async(name=name, **kwargs)

    def get_all(self, *args, **kwargs) -> dict[str, Any]:
        """Gets all items from the io object.

        Returns:
            The all items in the io objects.
        """
        return {k: v.get(*args, **kwargs) for k, v in self.data.items()}

    # Put
    def put_item(self, name: str, value: Any, *args: Any, **kwargs: Any) -> None:
        """Put an item into an IO object.

        Args:
            name: The key name to the IO object to put the item into.
            value: The value to put in the IO object.
            *args: The arguments of the put of the IO object.
            **kwargs: The keyword arguments of the put of the IO object.
        """
        self.data[name].put(value, *args, **kwargs)

    async def put_item_async(self, name: str, value: Any, *args: Any, **kwargs: Any) -> None:
        """Asynchronously put an item into an IO object.

        Args:
            name: The key name to the IO object to put the item into.
            value: The value to put in the IO object.
            *args: The arguments of the put of the IO object.
            **kwargs: The keyword arguments of the put of the IO object.
        """
        self.data[name].put_async(value, *args, **kwargs)

    def put_ordered(self, values: Iterable[Any], *args: Any, **kwargs: Any) -> None:
        """Puts given values into their IO objects based on this object's order.

        Args:
            values: The items to put.
            *args: The arguments of the put of the IO objects.
            **kwargs: The keyword arguments of the put of the IO objects.
        """
        for k, v in zip(self.order, values):
            self.data[k].put(v, *args, **kwargs)

    async def put_ordered_async(self, values: Iterable[Any], *args: Any, **kwargs: Any) -> None:
        """Asynchronously puts given values into their IO objects based on this object's order.

        Args:
            values: The items to put.
            *args: The arguments of the put of the IO objects.
            **kwargs: The keyword arguments of the put of the IO objects.
        """
        await gather(*(self.data[k].put_async(v, *args, **kwargs) for k, v in zip(self.order, values)))

    def put_all(self, __m: Any = None, /, **kwargs: Any) -> None:
        """Puts all given keyword IO values into their IO objects.

        Args:
            __m: A mapping with the IO values to put into IO objects.
            **kwargs: The IO values to put into IO objects.
        """
        for k, v in (kwargs if __m is None else (__m | kwargs)).items():
            self.data[k].put(v)

    async def put_all_async(self, __m: Any = None, /, **kwargs: Any) -> None:
        """Asynchronously puts all given keyword IO values into their IO objects.

        Args:
            __m: A mapping with the IO values to put into IO objects.
            **kwargs: The IO values to put into IO objects.
        """
        await gather(*(self.data[k].put_async(v) for k, v in (kwargs if __m is None else (__m | kwargs)).items()))

    def put_to_all(self, value: Any, *args, **kwargs: Any) -> None:
        """Puts a value to all IO objects.

        Args:
            value: The object to put into this object.
            *args: The arguments for the inner io objects' put.
            **kwargs: The keyword arguments for the inner io objects' put.
        """
        for io_object in self.data.values():
            io_object.put(value, *args, **kwargs)

    async def put_to_all_async(self, value: Any, *args, **kwargs: Any) -> None:
        """Asynchronously puts a value to all IO objects.

        Args:
            value: The object to put into this object.
            *args: The arguments for the inner io objects' put.
            **kwargs: The keyword arguments for the inner io objects' put.
        """
        await gather(*(io_object.put(value, *args, **kwargs) for io_object in self.data.values()))

    # IO Mapping
    def get_links(self) -> dict[str, IOMap] | None:
        """Gets the links of this IO object.

       Returns:
           The links of this IO object.
       """
        return {n: m.generate_io_map() for n, m in self.data}

