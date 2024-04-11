""" iorouter.py
An IO object which maps inputs to outputs.
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
from asyncio import gather, create_task
from collections.abc import Iterable, Callable
from functools import partial
from typing import ClassVar, Any
from types import MethodType
from weakref import WeakKeyDictionary, WeakSet

# Third-Party Packages #
from baseobjects import SentinelObject, search_sentinel
from baseobjects.collections import OrderableDict
from baseobjects.functions import MethodMultiplexer

# Local Packages #
from ..base import IOMap, BaseIO, BaseIOMultiplexer, IODelegator, IOWrapper
from ..containers import IOQueue


# Definitions #
# Classes #
class IORouter(BaseIOMultiplexer, OrderableDict):
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
    default_create_link: ClassVar[str] = "create_link_self"

    # Attributes #
    break_sentinel: SentinelObject = SentinelObject("io_break")
    default_io: type[BaseIO] = IOQueue

    required: tuple[str] = ()
    required_cache: BaseIO
    optional_defaults: dict[str, Any] = {}

    callback_method: Callable[[Any], None]
    callback_method_async: Callable[[Any], None]
    callback_tasks: set

    wrapped_getter: str | None = None
    wrapped_getter_async: str | None = None
    wrapped_putter: str | None = "put_required_callback"
    wrapped_putter_async: str | None = "put_required_callback_async"

    create_link: MethodMultiplexer
    directly_linked: WeakSet
    linked_to: dict[tuple[int, int, int, int], tuple[str, "IORouter", str]]
    linked_from: dict[tuple[int, int, int, int], tuple[str, "IORouter", str]]
    endpoints: dict[tuple[int, int, int, int], tuple["IORouter", str, "IORouter", str]]

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        io_: dict[str, BaseIO | None] | None = None,
        names: Iterable[str] | None = None,
        *args: Any,
        required_cache: BaseIO | None = None,
        init: bool = True,
        **kwargs: Any,
    ) -> None:
        # Attributes #
        self.optional_defaults = self.optional_defaults.copy()

        self.callback_tasks = set()

        self.create_link = MethodMultiplexer(instance=self, select=self.default_create_link)
        self.directly_linked = WeakSet()
        self.linked_to = {}
        self.linked_to = {}
        self.endpoints = {}

        # Parent Attributes #
        super().__init__()

        # Construction #
        if init:
            self.construct(io_, names, *args, required_cache=required_cache, **kwargs)

    # Pickling
    def __getstate__(self) -> dict[str, Any]:
        """Creates a dictionary of attributes which can be used to rebuild this object.

        Returns:
            A dictionary of this object's attributes.
        """
        state = super().__getstate__()
        if (directly_linked := state.get("directly_linked", None)) is not None:
            state["directly_linked"] = set(directly_linked)

        for name in ("callback_tasks", "directly_linked"):
            if name in state:
                del state[name]

        for name in ("callback_method", "callback_method_async"):
            if (m := state.get(name, None)) is not None and (_self_ := getattr(m, "_self_",  None)) is not None:
                # Create strong reference method
                state[name] = MethodType(m, _self_())

        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Builds this object based on a dictionary of corresponding attributes.

        Args:
            state: The attributes to build this object from.
        """
        super().__setstate__(state)
        self.callback_tasks = set()
        self.directly_linked = WeakSet()

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
        required_cache: BaseIO | None = None,
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

        if required_cache is not None:
            self.required_cache = required_cache
        else:
            self.required_cache = self.default_io()

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
                self.order.append(n)
            self.data[n] = type_(*args, **kwargs)

    def build_io(self, *args: Any, **kwargs: Any) -> None:
        for k, io_ in self.data.items():
            if (build_method := getattr(io_, "build_io", None)) is not None:
                build_method()

    def create_io_wrapper(self, name: str, *args: Any, **kwargs: Any) -> IOWrapper:

        getter = None if self.wrapped_getter is None else partial(getattr(self, self.wrapped_getter), name)
        if self.wrapped_getter_async is None:
            getter_async = None
        else:
            getter_async = partial(getattr(self, self.wrapped_getter_async), name)

        putter = None if self.wrapped_putter is None else partial(getattr(self, self.wrapped_putter), name)
        if self.wrapped_putter_async is None:
            putter_async = None
        else:
            putter_async = partial(getattr(self, self.wrapped_putter_async), name)

        return IOWrapper(getter, getter_async, putter, putter_async)

    # Linking
    def create_link_self(self, name: str, *args: Any, **kwargs: Any) -> BaseIO:
        return self

    def create_link_pass_io(self, name: str, *args: Any, **kwargs: Any) -> BaseIO:
        return self.data[name]

    def link_forward(
        self,
        name: str,
        io_: "IORouter",
        destination: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        key = (id(self), id(name), id(io_), id(destination))
        self.linked_to[key] = (name, io_, destination)
        io_.linked_from[key] = (destination, self, name)

        self.data[name] = io_ if destination is None else io_.create_link()

    def is_link_endpoint(self) -> bool:
        return False

    def get_link_endpoints(self, memo: dict | None = None) -> dict["IORouter", Any]:
        if memo is None:
            memo = {}

        for io_ in self.directly_linked:
            io_.get_link_endpoints(memo)

        for k, (n, io_, d) in self.linked_to.items():
            if io_.is_link_endpoint():
                memo[k] = (self, n, io_, d)
            else:
                io_.get_link_endpoints(memo)

        return memo

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

    # State
    def empty_io(self) -> dict[str, bool]:
        """Checks the IO objects in this object are empty.

        Returns:
            The result of checking all IO objects in this object.
        """
        return {k: v.empty() for k, v in self.data.items()}

    def empty_any(self) -> bool:
        """Checks if any of the IO objects in this object are empty.

        Returns:
            Returns True if any of the IO objects are empty, False otherwise.
        """
        return any(v.empty() for v in self.data.values())

    def empty_all(self) -> bool:
        """Checks if all the IO objects in this object are empty.

        Returns:
             Returns True if al the IO objects are empty, False otherwise.
        """
        return all(v.empty() for v in self.data.values())

    def poll_io(self) -> dict[str, bool]:
        """Polls the IO objects in this object.

        Returns:
            The result of polling the IO objects in this object.
        """
        return {k: v.poll() for k, v in self.data.items()}

    def poll_any(self) -> bool:
        """Checks if any of the IO objects in this object have an item in them.

        Returns:
            Returns True if any of the IO objects have an item in them, False otherwise.
        """
        return any(v.poll() for v in self.data.values())

    def poll_all(self) -> bool:
        """Checks if all the IO objects in this object have an item in them.

        Returns:
             Returns True if al the IO objects have an item in them, False otherwise.
        """
        return all(v.poll() for v in self.data.values())

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

    def get_ordered(self, *args, **kwargs) -> tuple[Any, ...]:
        """Gets an item from all the IO objects.

        Returns:
            The first item in all the IO objects.
        """
        return tuple(v.get(*args, **kwargs) for v in self.data.values())

    async def get_ordered_async(self, *args, **kwargs) -> tuple[Any, ...]:
        """Asynchronously gets an item from all the IO objects.

        Returns:
            The first item in all the IO objects.
        """
        return await gather(*(v.get_async(*args, **kwargs) for v in self.data.values()))

    def get_link_id(
        self,
        key: tuple[int, int, int, int],
        required: Iterable[str] | None = None,
        default: Any = search_sentinel,
        defaults: dict[str, Any] | None = None,
        *args,
        **kwargs,
    ) -> None:
        """Put an item into an IO object.

        Args:
            name: The key name to the IO object to put the item into.
            value: The value to put in the IO object.
            *args: The arguments of the put of the IO object.
            **kwargs: The keyword arguments of the put of the IO object.
        """
        name, io_, origin = self.linked_from[key]
        value = io_.get() if origin is None else io_.get_item(origin)
        self.data[name].put(value, *args, **kwargs)
        required = set((self.required or self.order) if required is None else required)

        if all(v.poll() for k, v in self.data.items() if k in required):
            if defaults is None:
                defaults = self.optional_defaults

            items = {}
            for k, v in self.data.items():
                if k in required:
                    items[k] = v.get(*args, **kwargs)
                else:
                    items[k] = v.get(*args, block=False, default=defaults[k] if k in defaults else default, **kwargs)
            # Callback
            self.callback_method(items)

            # Endpoint
            for k, (o, n, in_, d) in self.endpoints.items():
                in_.get_link_id(k)

    async def get_link_id_async(
        self,
        key: tuple[int, int, int, int],
        required: Iterable[str] | None = None,
        default: Any = search_sentinel,
        defaults: dict[str, Any] | None = None,
        *args,
        **kwargs,
    ) -> None:
        """Put an item into an IO object.

        Args:
            name: The key name to the IO object to put the item into.
            value: The value to put in the IO object.
            *args: The arguments of the put of the IO object.
            **kwargs: The keyword arguments of the put of the IO object.
        """
        name, io_, origin = self.linked_from[key]
        value = await (io_.get_async() if origin is None else io_.get_item_async(origin))
        await self.data[name].put_async(value, *args, **kwargs)
        required = set((self.required or self.order) if required is None else required)

        if all(v.poll() for k, v in self.data.items() if k in required):
            items = []
            for k, v in self.data.items():
                if k in required:
                    items.append(v.get_async(*args, **kwargs))
                else:
                    items.append(v.get_async(
                        *args,
                        block=False,
                        default=defaults[k] if k in defaults else default,
                        **kwargs
                    ))
            # Create Execute Task
            task = create_task(self.callback_method_async(dict(zip(self.data.keys(), await gather(*items)))))
            self.callback_tasks.add(task)
            task.add_done_callback(self.callback_tasks.discard)  # Have task remove its reference after completion

            # Create Endpoint Task
            for k, (o, n, in_, d) in self.endpoints.items():
                task = create_task(in_.get_link_id_async(k))
                self.callback_tasks.add(task)
                task.add_done_callback(self.callback_tasks.discard)

    def get_all(self, *args, **kwargs) -> dict[str, Any]:
        """Gets an item from all the IO objects.

        Returns:
            The first item in all the IO objects.
        """
        return {k: v.get(*args, **kwargs) for k, v in self.data.items()}

    async def get_all_async(self, *args, **kwargs) -> dict[str, Any]:
        """Asynchronously gets an item from all the IO objects.

        Returns:
            The first item in all the IO objects.
        """
        v = await gather(*(v.get_async(*args, **kwargs) for v in self.data.values()))
        return dict(zip(self.data.keys(), await gather(*(v.get_async(*args, **kwargs) for v in self.data.values()))))

    def get_required(
        self,
        required: Iterable[str] | None = None,
        default: Any = search_sentinel,
        defaults: dict[str, Any] | None = None,
        *args,
        **kwargs,
    ) -> dict[str, Any]:
        """Gets an item from all required IO objects.

        Returns:
            The first item in all the IO objects.
        """
        required = set((self.required or self.order) if required is None else required)

        if defaults is None:
            defaults = self.optional_defaults

        items = {}
        for k, v in self.data.items():
            if k in required:
                items[k] = v.get(*args, **kwargs)
            else:
                items[k] = v.get(*args, block=False, default=defaults[k] if k in defaults else default, **kwargs)
        return items

    async def get_required_async(
        self,
        required: Iterable[str] | None = None,
        default: Any = search_sentinel,
        defaults: dict[str, Any] | None = None,
        *args,
        **kwargs,
    ) -> dict[str, Any]:
        """Asynchronously gets an item from the required IO objects.

        Returns:
            The first item in all the IO objects.
        """
        required = set((self.required or self.order) if required is None else required)

        if defaults is None:
            defaults = self.optional_defaults

        items = []
        for k, v in self.data.items():
            if k in required:
                items.append(v.get_async(*args, **kwargs))
            else:
                items.append(v.get_async(
                    *args,
                    block=False,
                    default=defaults[k] if k in defaults else default,
                    **kwargs
                ))
        return dict(zip(self.data.keys(), await gather(*items)))

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
        print("putting")
        await gather(*(self.data[k].put_async(v, *args, **kwargs) for k, v in zip(self.order, values)))
        print(f"{tuple(v.poll() for k, v in self.data.items())}")

    def put_cache_required(
        self,
        name: str,
        value: Any,
        required: Iterable[str] | None = None,
        default: Any = search_sentinel,
        defaults: dict[str, Any] | None = None,
        *args,
        **kwargs,
    ) -> bool:
        """Put an item into an IO object.

        Args:
            name: The key name to the IO object to put the item into.
            value: The value to put in the IO object.
            *args: The arguments of the put of the IO object.
            **kwargs: The keyword arguments of the put of the IO object.
        """
        self.data[name].put(value, *args, **kwargs)
        required = set((self.required or self.order) if required is None else required)

        if all(v.poll() for k, v in self.data.items() if k in required):
            if defaults is None:
                defaults = self.optional_defaults

            items = {}
            for k, v in self.data.items():
                if k in required:
                    items[k] = v.get(*args, **kwargs)
                else:
                    items[k] = v.get(*args, block=False, default=defaults[k] if k in defaults else default, **kwargs)
            self.required_cache.put(items)
            return True
        else:
            return False

    async def put_cache_required_async(
        self,
        name: str,
        value: Any,
        required: Iterable[str] | None = None,
        default: Any = search_sentinel,
        defaults: dict[str, Any] | None = None,
        *args,
        **kwargs,
    ) -> bool:
        """Put an item into an IO object.

        Args:
            name: The key name to the IO object to put the item into.
            value: The value to put in the IO object.
            *args: The arguments of the put of the IO object.
            **kwargs: The keyword arguments of the put of the IO object.
        """
        await self.data[name].put_async(value, *args, **kwargs)
        required = set((self.required or self.order) if required is None else required)

        if all(v.poll() for k, v in self.data.items() if k in required):
            items = []
            for k, v in self.data.items():
                items.append(v.get_async(*args, **kwargs))
            else:
                items.append(v.get_async(
                    *args,
                    block=False,
                    default=defaults[k] if k in defaults else default,
                    **kwargs
                ))
            await self.required_cache.put_async(dict(zip(self.data.keys(), await gather(*items))))
            return True
        else:
            return False

    def put_required_callback(
        self,
        name: str,
        value: Any,
        required: Iterable[str] | None = None,
        default: Any = search_sentinel,
        defaults: dict[str, Any] | None = None,
        *args,
        **kwargs,
    ) -> None:
        """Put an item into an IO object.

        Args:
            name: The key name to the IO object to put the item into.
            value: The value to put in the IO object.
            *args: The arguments of the put of the IO object.
            **kwargs: The keyword arguments of the put of the IO object.
        """
        self.data[name].put(value, *args, **kwargs)
        required = set((self.required or self.order) if required is None else required)

        if all(v.poll() for k, v in self.data.items() if k in required):
            if defaults is None:
                defaults = self.optional_defaults

            items = {}
            for k, v in self.data.items():
                if k in required:
                    items[k] = v.get(*args, **kwargs)
                else:
                    items[k] = v.get(*args, block=False, default=defaults[k] if k in defaults else default, **kwargs)
            # Callback
            self.callback_method(items)

            # Endpoint
            for k, (o, n, in_, d) in self.endpoints.items():
                in_.get_link_id(k)

    async def put_required_callback_async(
        self,
        name: str,
        value: Any,
        required: Iterable[str] | None = None,
        default: Any = search_sentinel,
        defaults: dict[str, Any] | None = None,
        *args,
        **kwargs,
    ) -> None:
        """Put an item into an IO object.

        Args:
            name: The key name to the IO object to put the item into.
            value: The value to put in the IO object.
            *args: The arguments of the put of the IO object.
            **kwargs: The keyword arguments of the put of the IO object.
        """
        await self.data[name].put_async(value, *args, **kwargs)
        required = set((self.required or self.order) if required is None else required)

        if all(v.poll() for k, v in self.data.items() if k in required):
            if defaults is None:
                defaults = self.optional_defaults

            items = []
            for k, v in self.data.items():
                if k in required:
                    items.append(v.get_async(*args, **kwargs))
                else:
                    items.append(v.get_async(
                        *args,
                        block=False,
                        default=defaults[k] if k in defaults else default,
                        **kwargs
                    ))
            # Create Execute Task
            task = create_task(self.callback_method_async(dict(zip(self.data.keys(), await gather(*items)))))
            self.callback_tasks.add(task)
            task.add_done_callback(self.callback_tasks.discard)  # Have task remove its reference after completion

            # Create Endpoint Task
            for k, (o, n, in_, d) in self.endpoints.items():
                task = create_task(in_.get_link_id_async(k))
                self.callback_tasks.add(task)
                task.add_done_callback(self.callback_tasks.discard)

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

    def put_break_sentinel(self, *args, **kwargs: Any) -> None:
        """Puts the break sentinel to all IO objects.

        Args:
            value: The object to put into this object.
            *args: The arguments for the inner io objects' put.
            **kwargs: The keyword arguments for the inner io objects' put.
        """
        for io_object in self.data.values():
            io_object.put(self.break_sentinel, *args, **kwargs)

    async def put_break_sentinel_async(self, *args, **kwargs: Any) -> None:
        """Asynchronously puts the break sentinel to all IO objects.

        Args:
            value: The object to put into this object.
            *args: The arguments for the inner io objects' put.
            **kwargs: The keyword arguments for the inner io objects' put.
        """
        await gather(*(io_object.put(self.break_sentinel, *args, **kwargs) for io_object in self.data.values()))

    # IO Mapping
    def get_links(self) -> dict[str, IOMap] | None:
        """Gets the links of this IO object.

       Returns:
           The links of this IO object.
       """
        return {n: m.generate_io_map() for n, m in self.data}

    # Callback
    def set_callback_methods(self, method, method_async) -> None:
        self.callback_method = method
        self.callback_method_async = method_async
