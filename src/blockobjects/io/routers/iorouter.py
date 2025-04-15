""" iorouter.py
An IO object which maps inputs to outputs.
"""
from h5py.h5pl import append

# Header #
__package_name__ = "blockobjects"

__author__ = "Anthony Fong"
__credits__ = ["Anthony Fong"]
__copyright__ = "Copyright 2022, Anthony Fong"
__license__ = "MIT"

__version__ = "0.1.0"


# Imports #
# Standard Libraries #
from asyncio import gather, create_task, Task, wait_for, shield
from collections.abc import Iterable, Iterator, Callable, MutableMapping
from collections import deque
from functools import partial
from itertools import chain
from typing import ClassVar, Any
from types import FunctionType, MethodType
from uuid import uuid4
from weakref import WeakKeyDictionary, WeakSet, ReferenceType

# Third-Party Packages #
from baseobjects import SentinelObject, DEFAULTSENTINEL, BaseReducible
from baseobjects.collections import OrderableDict, DeepChainMap
from baseobjects.functions import MethodMultiplexer
from baseobjects.objects import CallbackManager

# Local Packages #
from ...process import AsyncQueue
from ..base import IOMap, BaseIO, IOTerminus, BaseIOMultiplexer, IOForwarder, IOWrapper
from .basecallbackrouting import BaseCallbackRouting
from .iocallbackwrapper import IOCallbackWrapper


# Definitions #
# Typing #
type IOGroupType = MutableMapping[str | int, BaseIO ]
type IOGroupTypeMap = MutableMapping[str, IOGroupType]

# Functions #
async def _put_loading_async(put_method: Callable, callback: Task) -> None:
    await put_method(await callback)


# Classes #
class IORouter(BaseIOMultiplexer, BaseCallbackRouting, BaseReducible):
    """An IO object which maps inputs to outputs, facilitating the routing of data between different IO objects.

    It supports synchronous and asynchronous operations, allowing for flexible data handling in various contexts.

    Class Attributes:
        default_get: The default method name for synchronous get operations.
        default_get_async: The default method name for asynchronous get operations.
        default_put: The default method name for synchronous put operations.
        default_put_async: The default method name for asynchronous put operations.
        default_create_link: The default method name for creating links between IO objects.

    Attributes:
        break_sentinel: A sentinel object used to indicate a break condition in IO operations.
        default_io_type: The default IO object type to use when constructing new IO objects.
        required: A tuple of required IO object names for certain operations, or None if not applicable.
        optional_defaults: A dictionary of default values for optional IO objects.
        id_number: A unique identifier for the IORouter instance.
        create_link: A multiplexer for managing link creation methods.
        directly_linked: A set of directly linked IO objects.
        links_to: A dictionary mapping links from this router to others.
        links_from: A dictionary mapping links to this router from others.
        endpoints: A dictionary of endpoint links.
        endpoint_tasks: A set of asyncio tasks associated with endpoint operations.
        get_tasks: A set of asyncio tasks associated with get operations.
        put_tasks: A set of asyncio tasks associated with put operations.
        _is_listening: A flag indicating whether the router is currently listening for incoming data.
        scheduled_listener_links: A set of links scheduled for listening.
        listeners: A dictionary of active listener tasks.
        callback: A synchronous callback function to be executed upon certain conditions.
        callback_async: An asynchronous callback function to be executed upon certain conditions.
        callback_executor: The current task executing the asynchronous callback, if any.
        max_callback_tasks: The maximum number of concurrent callback tasks allowed.
        callback_tasks: A set of asyncio tasks associated with callback operations.

    Args:
        io_: Initial mapping of names to IO objects, or None for default initialization.
        names: An iterable of names for IO objects, or None if not applicable.
        *args: Additional positional arguments passed to parent class constructors.
        init: Determines whether the object should perform initialization operations.
        **kwargs: Additional keyword arguments passed to parent class constructors.
    """

    # Class Attributes #
    default_get: ClassVar[str] = "get_all"
    default_get_async: ClassVar[str] = "get_all_async"
    default_put: ClassVar[str] = "put_to_all"
    default_put_async: ClassVar[str] = "put_to_all_async"
    default_join: ClassVar[str] = "join_all"
    default_join_async: ClassVar[str] = "join_all_async"
    default_create_link: ClassVar[str] = "create_link_wrapper"

    # Class Methods #
    @classmethod
    def is_endpoint_link(cls, source: "IORouter", destination: "IORouter") -> bool:
        s_parent = source.parent
        d_parent = destination.parent
        if (source is d_parent or
            destination is s_parent or
            (s_parent is not None and d_parent is not None and s_parent.parent is d_parent)
        ):
            return False
        else:
            return source.is_remote() and not destination.is_remote()

    @classmethod
    def is_listen_link(cls, source: "IORouter", destination: "IORouter") -> bool:
        return cls.is_endpoint_link(source, destination)

    # Attributes #
    name: str = ""
    break_sentinel: SentinelObject = SentinelObject("io_break")

    # Links
    id_number: int
    _parent: ReferenceType["IORouter"] | None = None
    create_link: MethodMultiplexer
    directly_linked: WeakSet
    links_to: dict[tuple[int, str, int, str], "IORouter"]
    links_from: dict[tuple[int, str, int, str], "IORouter"]
    endpoints: dict[tuple[int, str, int, str], tuple["IORouter", str, "IORouter", str]]
    endpoint_tasks: set[Task]

    # IO
    hidden_groups: set[str] = set()
    _visible_groups: set[str] | None = None
    default_io_type: type[BaseIO] = IOTerminus
    default_io_listen_container_type: type[BaseIO] = AsyncQueue
    default_values: dict[str, dict[str, Any]] = {}

    io_objects: DeepChainMap[str | int, BaseIO]
    io_groups: IOGroupTypeMap
    encapsulated_routers: MutableMapping[int, "IORouter"]

    # Get/Put Tasks
    encapsulated_wrappers: dict[tuple, BaseIO]
    wrapped_getter: str | None = "get_item"
    wrapped_getter_async: str | None = "get_item_async"
    wrapped_putter: str | None = "put_item"
    wrapped_putter_async: str | None = "put_item_async"

    get_tasks: set[Task]
    put_tasks: set[Task]

    # Listening
    _is_listening: bool = True
    listener_functions: dict[str, [IOWrapper, IOWrapper]]
    scheduled_listener_links: set[tuple[int, str, int, str]]
    listeners: dict[str, Task]

    # Properties
    @property
    def parent(self) -> "IORouter":
        return self._parent if self._parent is None else self._parent()

    @parent.setter
    def parent(self, parent: "IORouter") -> None:
        self.set_parent(parent)

    @property
    def visible_groups(self) -> set[str]:
        return set(self.io_groups.keys()) - self.hidden_groups if self._visible_groups is None else self._visible_groups

    @visible_groups.setter
    def visible_groups(self, groups: set[str] | None) -> None:
        self._visible_groups = groups

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        io_: IOGroupTypeMap | MutableMapping[str, Iterable[str | int]] | Iterable[str | int] | None = None,
        visible_groups: Iterable[str] | None | SentinelObject = DEFAULTSENTINEL,
        hidden_groups: Iterable[str] | None = None,
        *args: Any,
        name: str | None = None,
        default_io_type: type[BaseIO] | None = None,
        init: bool = True,
        **kwargs: Any,
    ) -> None:
        # Attributes #
        self.id_number = uuid4().int
        self.name = f"{self.__class__.__name__}_{self.id_number}" if name is None else name

        self.default_values = self.default_values.copy()

        self.create_link = MethodMultiplexer(instance=self, select=self.default_create_link)
        self.directly_linked = WeakSet()
        self.links_to = {}
        self.links_from = {}
        self.endpoints = {}
        self.endpoint_tasks = set()

        self.hidden_groups = self.hidden_groups.copy()
        if self._visible_groups is not None:
            self.visible_groups = self.visible_groups.copy()

        __default__ = OrderableDict()
        self.io_objects = DeepChainMap(__default__)
        self.io_groups = {"__default__": __default__}
        self.encapsulated_routers = OrderableDict()

        self.encapsulated_wrappers = {}
        self.get_tasks = set()
        self.put_tasks = set()

        self.listener_functions = {}
        self.scheduled_listener_links = set()
        self.listeners = dict()

        # Parent Attributes #
        super().__init__(init=False)

        # Construction #
        if init:
            self.construct(
                io_,
                visible_groups,
                hidden_groups,
                *args,
                default_io_type=default_io_type,
                **kwargs,
            )

    # Pickling
    def __getstate__(self) -> None | dict[str, Any] | tuple[dict[str, Any] | None, dict[str, Any]]:
        """Gets the object's state for pickling.

        Returns:
            The state returned will be either of the following types based on the presence of __dict__ and __slots__:
                None: __dict__ nor __slots__ are present.
                dict: __dict__ is present and __slots__ is not present.
                tuple[None, dict]: __dict__ is not present and __slots__ is present.
                tuple[dict, dict]: __dict__ is present and __slots__ is present.
        """
        state = super().__getstate__()
        if (directly_linked := state.get("directly_linked", None)) is not None:
            state["directly_linked"] = set(directly_linked)

        for name in ("get_tasks", "put_tasks", "listeners", "callback_tasks", "directly_linked", "_parent"):
            if name in state:
                del state[name]

        return state

    def __setstate__(self, state: Any) -> None:
        """Sets the object's state from a pickled state.

        By default, the state can be one of the following types with the corresponding behavior:
            None: Will not set any state.
            dict: Will set the __dict__ attribute to the state.
            tuple[None, dict]: Will set the slot values to the second dict of the tuple.
            tuple[dict, dict]: Will set the __dict__ attribute to the first dict of the tuple and set the slot values
                to the second dict of the tuple.

        Args:
            state: An object which can be used to set the state of this object.
        """
        super().__setstate__(state)
        self.get_tasks = set()
        self.put_tasks = set()
        self.listeners = dict()
        self.callback_tasks = set()
        self.directly_linked = WeakSet(state.get("directly_linked", None))
        if hasattr(self, "io_groups"):
            for en in self.encapsulated_routers.values():
                en._parent = ReferenceType(self)

    # Set Item
    def __setitem__(self, key: str, item: BaseIO) -> None:
        """Sets an IO within this manager. If an existing IO is an IOForwarder, set it to

        Args:
            key: The name of the IO to set.
            item: The IO object to set.
        """
        if (io_object := self.io_objects.get(key, None)) is not None and isinstance(io_object, IOForwarder):
            io_object.io = item
        else:
            self.io_objects[key] = item

    # Representation
    def __repr__(self) -> str:
        return f"<{self.name}: {super().__repr__()}>"

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        io_: IOGroupTypeMap | MutableMapping[str, Iterable[str | int]] | Iterable[str | int] | None = None,
        visible_groups: Iterable[str] | None | SentinelObject = DEFAULTSENTINEL,
        hidden_groups: Iterable[str] | None = None,
        *args: Any,
        name: str | None = None,
        default_io_type: type[BaseIO] | None = None,
        **kwargs: Any,
    ) -> None:
        """Constructs this object.

        Args:
            io_: The input/outputs to be managed.
            *args: Arguments for inheritance.
            **kwargs: Keyword arguments for inheritance.
        """
        if name is not None:
            self.name = name

        if default_io_type is not None:
            self.default_io_type = default_io_type

        match io_:
            case MutableMapping():
                match next(iter(io_.values()), None):
                    case MutableMapping():
                        self.require_io_groups(io_)
                    case _:
                        self.create_ios(groups=io_)
            case str():
                self.create_io(io_)
            case Iterable():
                self.create_ios(names=io_)

        if visible_groups is not DEFAULTSENTINEL:
            self._visible_groups = visible_groups if visible_groups is not None else set(visible_groups)

        if hidden_groups is not None:
            self.hidden_groups.clear()
            self.hidden_groups.update(hidden_groups)

        super().construct(*args, **kwargs)

    # State
    def get_id_number(self) -> int:
        return self.id_number

    async def get_id_number_async(self) -> int:
        return self.id_number

    def empty_io(self) -> dict[str, bool]:
        """Checks the IO objects in this object are empty.

        Returns:
            The result of checking all IO objects in this object.
        """
        return {k: v.empty() for k, v in self.iter_visible_io_items()}

    def empty_any(self) -> bool:
        """Checks if any visible IO objects in this object are empty.

        Returns:
            Returns True if any of the IO objects are empty, False otherwise.
        """
        return any(v.empty() for v in self.iter_visible_io_values())

    def empty_all(self) -> bool:
        """Checks if all visible IO objects in this object are empty.

        Returns:
             Returns True if al the IO objects are empty, False otherwise.
        """
        return all(v.empty() for v in self.iter_visible_io_values())

    def poll_io(self) -> dict[str, bool]:
        """Polls the IO objects in this object.

        Returns:
            The result of polling the IO objects in this object.
        """
        return {k: v.poll() for k, v in self.iter_visible_io_items()}

    def poll_any(self) -> bool:
        """Checks if any visible IO objects in this object have an item in them.

        Returns:
            Returns True if any of the IO objects have an item in them, False otherwise.
        """
        return any(v.poll() for v in self.iter_visible_io_values())

    def poll_all(self) -> bool:
        """Checks if all visible IO objects in this object have an item in them.

        Returns:
             Returns True if al the IO objects have an item in them, False otherwise.
        """
        return all(v.poll() for v in self.iter_visible_io_values())

    def poll_all_ios(self, names: Iterable[str]) -> bool:
        """Checks if all given IO objects in this object have an item in them.

        Returns:
             Returns True if al the IO objects have an item in them, False otherwise.
        """
        return all(self.io_objects[n].poll() for n in names)

    async def poll_all_ios_async(self, names: Iterable[str]) -> bool:
        """Asynchronously, checks if all given IO objects in this object have an item in them.

        Returns:
             Returns True if al the IO objects have an item in them, False otherwise.
        """
        return all(self.io_objects[n].poll() for n in names)

    def poll_groups(self, *args: str, groups: Iterable[str] | str | None) -> bool:
        """Checks if all IO objects within given groups have an item in them.

        Args:
            *args: The names of the groups to poll
            groups: Either an iterable of the groups to poll or string of a group to poll.

        Returns:
            True if all IO objects have an item in them.
        """
        return all(v.poll() for v in self.iter_groups_io_values(*args, groups=groups))

    async def poll_groups_async(self, *args: str, groups: Iterable[str] | str | None) -> bool:
        """Asynchronously, checks if all IO objects within given groups have an item in them.

        Args:
            *args: The names of the groups to poll
            groups: Either an iterable of the groups to poll or string of a group to poll.

        Returns:
            True if all IO objects have an item in them.
        """
        return all(v.poll() for v in self.iter_groups_io_values(*args, groups=groups))

    def is_remote(self) -> bool:
        """Checks if this object is remote."""
        return self.parent.is_remote() if self.parent is not None else False

    # Ordering
    def get_order(self) -> tuple[str, ...]:
        return tuple(self.iter_visible_io_keys())

    def ordered_to_dict(self, ordered: Iterable[Any]) -> dict[str, Any]:
        """Creates a dictionary from an ordered iterable based on the order of this IO.

        Args:
            ordered: The ordered iterable to create a dictionary from.

        Returns:
            The dictionary of the ordered items.
        """
        return dict(zip(self.iter_visible_io_keys(), ordered))

    def dict_to_ordered(self, dict_: dict[str, Any]) -> tuple[Any, ...]:
        """Creates an ordered tuple from dictionary based on the order of this IO.

        Args:
            dict_: The dictionary to create an ordered tuple from.

        Returns:
            The tuple of the ordered items.
        """
        return tuple(dict_.get(name) for name in self.iter_visible_io_keys())

    # IO Objects
    def require_io_group(
        self,
        group: str,
        io_: IOGroupType | None,
    ) -> MutableMapping[str | int, BaseIO]:
        if (g := self.io_groups.get(group, None)) is None:
            self.io_groups[group] = g = OrderableDict(io_)
            self.io_objects.maps.append(g)
        return g

    def require_io_groups(
        self,
        groups: IOGroupTypeMap,
    ) -> dict[str, MutableMapping[str | int, BaseIO]]:
        return {n: self.require_io_group(n, io_) for n, io_ in groups.items()}

    def pop_io_group(self, group: str) -> MutableMapping[str | int, BaseIO]:
        g = self.io_groups.pop(group)
        self.io_objects.maps.remove(g)
        return g

    def delete_io_group(self, group: str) -> None:
        g = self.io_groups.pop(group)
        self.io_objects.maps.remove(g)

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
        if type_ is None:
            type_ = self.default_io_type

        io_ = type_(*args, **kwargs)

        if (g := self.io_groups.get(group, None)) is None:
            self.io_groups[group] = g = OrderableDict(((name, io_),))
            self.io_objects.maps.append(g)
        else:
            g[name] = io_

        return io_

    def create_ios(
        self,
        names: Iterable[str | int] | None = None,
        group: str = "__default__",
        groups: MutableMapping[str, Iterable[str | int]] | None = None,
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
        if type_ is None:
            type_ = self.default_io_type

        groups = groups or {} | {} if names is None else {group: names}

        new_groups = {}
        for group_name, io_names in groups.items():
            new_groups[group_name] = ios = {n: type_(*args, **kwargs) for n in io_names}
            if (g := self.io_groups.get(group_name, None)) is None:
                self.io_groups[group_name] = g = OrderableDict(ios)
                self.io_objects.maps.append(g)
            else:
                g.update(ios)

        return new_groups

    def require_io(
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
        if type_ is None:
            type_ = self.default_io_type

        if (io_ := self.io_groups.get(group, {}).get(name, None)) is None:
            io_ = type_(*args, **kwargs)

            if (g := self.io_groups.get(group, None)) is None:
                self.io_groups[group] = g = OrderableDict(((name, io_),))
                self.io_objects.maps.append(g)
            else:
                g[name] = io_

        return io_

    def build_io(self, *args: Any, **kwargs: Any) -> None:
        for k, io_ in self.iter_visible_io_items():
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

    def set_io(self, name: str, io_: BaseIO) -> None:
        self.io_objects[name] = io_

    async def set_io_async(self, name: str, io_: BaseIO) -> None:
        self.io_objects[name] = io_

    def get_deepest(self) -> dict:
        visible = chain.from_iterable(self.io_groups.get(n, {}).items() for n in self.visible_groups)
        return {k: (v.get_deepest() if isinstance(v, IORouter) else v) for k, v in visible}

    def set_deepest(self, io_: dict[str, BaseIO | None]) -> None:
        for k, v in io_.items():
            if isinstance(v, dict):
                self.io_objects[k].set_deepest(v)
            else:
                self.io_objects[k] = v

    async def set_deepest_async(self, io_: dict[str, BaseIO | None]) -> None:
        for k, v in io_.items():
            if isinstance(v, dict):
                self.io_objects[k].set_deepest(v)
            else:
                self.io_objects[k] = v

    def set_inner_io_iter(self, key: str | int, keys: Iterator, io_: BaseIO) -> None:
        try:
            next_key = next(keys)
        except StopIteration:
            self.set_io(key, io_)
        else:
            self.io_objects[key].set_inner_io_iter(next_key, keys, io_)

    async def set_inner_io_iter_async(self, key: str | int, keys: Iterator, io_: BaseIO) -> None:
        try:
            next_key = next(keys)
        except StopIteration:
            await self.set_io_async(key, io_)
        else:
            await self.io_objects[key].set_inner_io_iter_async(next_key, keys, io_)

    def set_inner_io(self, keys: Iterable[str | int] | str, io_: BaseIO) -> None:
        if isinstance(keys, str):
            self.io_objects[keys].set_io(keys, io_)
        else:
            key_iter = iter(keys)
            key = next(key_iter)
            self.set_inner_io_iter(key, key_iter, io_)

    async def set_inner_io_async(self, keys: Iterable[str | int] | str, io_: BaseIO) -> None:
        if isinstance(keys, str):
            await self.io_objects[keys].set_io_aysnc(keys, io_)
        else:
            key_iter = iter(keys)
            key = next(key_iter)
            await self.set_inner_io_iter_async(key, key_iter, io_)

    def iter_groups_io_keys(self, *args: str, groups: Iterable[str] | str | None) -> Iterable[str]:
        group_names = args if groups is None else chain(args, (groups,) if isinstance(groups, str) else groups)
        return chain.from_iterable(self.io_groups.get(n, {}).keys() for n in group_names)

    def iter_groups_io_values(self, *args, groups: Iterable[str] | str | None) -> Iterable[BaseIO]:
        group_names = args if groups is None else chain(args, (groups,) if isinstance(groups, str) else groups)
        return chain.from_iterable(self.io_groups.get(n, {}).values() for n in group_names)

    def iter_groups_io_items(self, *args, groups: Iterable[str] | str | None) -> Iterable[tuple[str, BaseIO]]:
        group_names = args if groups is None else chain(args, (groups,) if isinstance(groups, str) else groups)
        return chain.from_iterable(self.io_groups.get(n, {}).items() for n in group_names)

    def iter_visible_io_keys(self) -> Iterable[str]:
        return chain.from_iterable(self.io_groups.get(n, {}).keys() for n in self.visible_groups)

    def iter_visible_io_values(self) -> Iterable[BaseIO]:
        return chain.from_iterable(self.io_groups.get(n, {}).values() for n in self.visible_groups)

    def iter_visible_io_items(self) -> Iterable[tuple[str, BaseIO]]:
        return chain.from_iterable(self.io_groups.get(n, {}).items() for n in self.visible_groups)

    # Get
    def get_item(self, name: str | int, **kwargs: Any) -> Any:
        """Gets an item from the requested IO object.

        Args:
            name: The name of tje IO object to get an item from.
            **kwargs: The keyword arguments for getting the item from the requested IO object.

        Returns:
            The requested item.
        """
        return self.io_objects[name].get(**kwargs)

    async def get_item_async(self, name: str | int, **kwargs: Any) -> Any:
        """Asynchronously gets an item from the requested IO object.

        Args:
            name: The name of tje IO object to get an item from.
            **kwargs: The keyword arguments for getting the item from the requested IO object.

        Returns:
            The requested item.
        """
        task = create_task(self.io_objects[name].get_async(**kwargs))
        self.get_tasks.add(task)
        task.add_done_callback(self.get_tasks.discard)
        return await task

    def get_items(
        self,
        names: Iterable[str | int],
        defaults: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        # Set empty defaults
        if defaults is None:
            defaults = {}

        # Build items from iterators
        r_iter = ((n, self.io_objects[n].get(*args, **kwargs)) for n in names)
        o_iter = ((k, self.io_objects[k].get(*args, block=False, default=v, **kwargs)) for k, v in defaults.items())
        return dict(chain(r_iter, o_iter))

    async def get_items_async(
        self,
        names: Iterable[str],
        defaults: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any]:
        # Set empty defaults
        if defaults is None:
            defaults = {}

        # Build items from iterators
        r_iter = ((n, create_task(self.io_objects[n].get_async(*args, **kwargs))) for n in names)
        o_iter = (
            (k, create_task(self.io_objects[k].get_async(*args, block=False, default=v, **kwargs)))
            for k, v in defaults.items()
        )
        tasks = dict(chain(r_iter, o_iter))

        # Track tasks in get tasks
        for v in tasks.values():
            v.add_done_callback(self.get_tasks.discard)
            self.get_tasks.add(v)

        # Build items with an async gather
        return dict(zip(tasks.keys(), await gather(*tasks.values())))

    def get_ordered(self, *args, **kwargs) -> list[Any, ...]:
        """Gets an item from all the IO objects.

        Returns:
            The first item in all the IO objects.
        """
        return list(v.get(*args, **kwargs) for v in self.io_objects.values())

    async def get_ordered_async(self, *args, **kwargs) -> list[Any, ...]:
        """Asynchronously gets an item from all the IO objects.

        Returns:
            The first item in all the IO objects.
        """
        tasks = set
        for v in self.io_objects.values():
            t = create_task(v.get_async(*args, **kwargs))
            tasks.add(t)
            t.add_done_callback(self.get_tasks.discard)
        self.get_tasks.update(tasks)
        return await gather(*tasks)

    def get_all(self, *args, **kwargs) -> dict[str, Any]:
        """Gets an item from all the IO objects.

        Returns:
            The first item in all the IO objects.
        """
        return {k: v.get(*args, **kwargs) for k, v in self.iter_visible_io_items()}

    async def get_all_async(self, *args, **kwargs) -> dict[str, Any]:
        """Asynchronously gets an item from all the IO objects.

        Returns:
            The first item in all the IO objects.
        """
        tasks = deque()
        keys = deque()
        for k, v in self.iter_visible_io_items():
            keys.append(k)
            t = create_task(v.get_async(*args, **kwargs))
            tasks.append(t)
            t.add_done_callback(self.get_tasks.discard)
        self.get_tasks.update(tasks)
        return dict(zip(keys, await gather(*tasks)))

    def get_groups(
        self,
        groups: Iterable[str] | str = "__default__",
        defaults: dict[str, Any] | None = None,
        *args,
        **kwargs,
    ) -> dict[str, Any]:
        """Gets an item from all required IO objects.

        Returns:
            The first item in all the IO objects.
        """
        defaults = self.default_values | (defaults or {})

        items = {}
        for k, v in self.iter_groups_io_items(groups=groups):
            if (default := defaults.get(k, None)) is None:
                items[k] = v.get(*args, **kwargs)
            else:
                items[k] = v.get(*args, block=False, default=default, **kwargs)

        return items

    async def get_groups_async(
        self,
        groups: Iterable[str] | str = "__default__",
        defaults: dict[str, Any] | None = None,
        *args,
        **kwargs,
    ) -> dict[str, Any]:
        """Asynchronously gets an item from the required IO objects.

        Returns:
            The first item in all the IO objects.
        """
        defaults = self.default_values | (defaults or {})

        tasks = deque()
        keys = deque()
        for k, v in self.iter_groups_io_items(groups=groups):
            keys.append(k)
            if (default := defaults.get(k, None)) is None:
                t = create_task(v.get_async(*args, **kwargs))
            else:
                t = create_task(v.get_async(*args, block=False, default=default, **kwargs))
            tasks.append(t)
            t.add_done_callback(self.get_tasks.discard)
        self.get_tasks.update(tasks)
        return dict(zip(keys, await gather(*tasks)))

    def get_link_id(self, key: tuple[int, str, int, str], *args: Any, **kwargs: Any) -> None:
        _, _, id_, name = key
        if id_ == self.id_number:
            return self.io_objects[name].get(*args, **kwargs)
        else:
            raise KeyError(f"ID missmatch for {key}: {id_} != {self.id_number}")

    async def get_link_id_async(self, key: tuple[int, str, int, str], *args: Any, **kwargs: Any) -> None:
        _, _, id_, name = key
        if id_ == self.id_number:
           return await self.io_objects[name].get_async(*args, **kwargs)
        else:
            raise KeyError(f"ID missmatch for {key}: {id_} != {self.id_number}")

    # Put
    def put_item(self, name: str, value: Any, *args: Any, **kwargs: Any) -> None:
        """Put an item into an IO object.

        Args:
            name: The key name to the IO object to put the item into.
            value: The value to put in the IO object.
            *args: The arguments of the put of the IO object.
            **kwargs: The keyword arguments of the put of the IO object.
        """
        self.io_objects[name].put(value, *args, **kwargs)

    async def put_item_async(self, name: str, value: Any, *args: Any, **kwargs: Any) -> None:
        """Asynchronously put an item into an IO object.

        Args:
            name: The key name to the IO object to put the item into.
            value: The value to put in the IO object.
            *args: The arguments of the put of the IO object.
            **kwargs: The keyword arguments of the put of the IO object.
        """
        await self.io_objects[name].put_async(value, *args, **kwargs)

    def put_item_value(self, value: Any, name: str,  *args: Any, **kwargs: Any) -> None:
        """Put an item into an IO object.

        Args:
            value: The value to put in the IO object.
            name: The key name to the IO object to put the item into.
            *args: The arguments of the put of the IO object.
            **kwargs: The keyword arguments of the put of the IO object.
        """
        self.io_objects[name].put(value, *args, **kwargs)

    async def put_item_value_async(self, value: Any, name: str, *args: Any, **kwargs: Any) -> None:
        """Asynchronously put an item into an IO object.

        Args:
            value: The value to put in the IO object.
            name: The key name to the IO object to put the item into.
            *args: The arguments of the put of the IO object.
            **kwargs: The keyword arguments of the put of the IO object.
        """
        await self.io_objects[name].put_async(value, *args, **kwargs)

    def put_ordered(self, values: Iterable[Any], *args: Any, **kwargs: Any) -> None:
        """Puts given values into their IO objects based on this object's order.

        Args:
            values: The items to put.
            *args: The arguments of the put of the IO objects.
            **kwargs: The keyword arguments of the put of the IO objects.
        """
        for k, v in zip(self.iter_visible_io_keys(), values):
            self.io_objects[k].put(v, *args, **kwargs)

    async def put_ordered_async(self, values: Iterable[Any], *args: Any, **kwargs: Any) -> None:
        """Asynchronously puts given values into their IO objects based on this object's order.

        Args:
            values: The items to put.
            *args: The arguments of the put of the IO objects.
            **kwargs: The keyword arguments of the put of the IO objects.
        """
        items = zip(self.iter_visible_io_keys(), values)
        await gather(*(self.io_objects[k].put_async(v, *args, **kwargs) for k, v in items))

    def put_items(self, items: dict[str, Any], *args: Any, **kwargs: Any) -> None:
        """Puts an item into an IO object and schedule a callback.

        Args:
            name: The key name to the IO object to put the item into.
            value: The value to put in the IO object.
            *args: The arguments of the put of the IO object.
            **kwargs: The keyword arguments of the put of the IO object.
        """
        # Put data into IO
        for name, value in items.items():
            self.io_objects[name].put(value, *args, **kwargs)

    async def put_items_async(self, items: dict[str, Any], *args: Any, **kwargs: Any) -> None:
        """Put an item into an IO object.

        Args:
            name: The key name to the IO object to put the item into.
            value: The value to put in the IO object.
            *args: The arguments of the put of the IO object.
            **kwargs: The keyword arguments of the put of the IO object.
        """
        # Put data into IO
        tasks = deque()
        for k, v in items.items():
            t = create_task(self.io_objects[k].put_async(v, *args, **kwargs))
            tasks.append(t)
            t.add_done_callback(self.put_tasks.discard)
        self.put_tasks.update(tasks)
        await gather(*tasks)

    def put_all(self, __m: Any = None, /, **kwargs: Any) -> None:
        """Puts all given keyword IO values into their IO objects.

        Args:
            __m: A mapping with the IO values to put into IO objects.
            **kwargs: The IO values to put into IO objects.
        """
        for k, v in (kwargs if __m is None else (__m | kwargs)).items():
            self.io_objects[k].put(v)

    async def put_all_async(self, __m: Any = None, /, **kwargs: Any) -> None:
        """Asynchronously puts all given keyword IO values into their IO objects.

        Args:
            __m: A mapping with the IO values to put into IO objects.
            **kwargs: The IO values to put into IO objects.
        """
        await gather(*(self.io_objects[k].put_async(v) for k, v in (kwargs if __m is None else (__m | kwargs)).items()))

    def put_to_all(self, value: Any, *args, **kwargs: Any) -> None:
        """Puts a value to all IO objects.

        Args:
            value: The object to put into this object.
            *args: The arguments for the inner io objects' put.
            **kwargs: The keyword arguments for the inner io objects' put.
        """
        for io_object in self.iter_visible_io_values():
            io_object.put(value, *args, **kwargs)

    async def put_to_all_async(self, value: Any, *args, **kwargs: Any) -> None:
        """Asynchronously puts a value to all IO objects.

        Args:
            value: The object to put into this object.
            *args: The arguments for the inner io objects' put.
            **kwargs: The keyword arguments for the inner io objects' put.
        """
        await gather(*(io_object.put_async(value, *args, **kwargs) for io_object in self.iter_visible_io_values()))

    def put_break_sentinel(self, *args, **kwargs: Any) -> None:
        """Puts the break sentinel to all IO objects.

        Args:
            value: The object to put into this object.
            *args: The arguments for the inner io objects' put.
            **kwargs: The keyword arguments for the inner io objects' put.
        """
        for io_object in self.io_objects.values():
            io_object.put(self.break_sentinel, *args, **kwargs)

    async def put_break_sentinel_async(self, *args, **kwargs: Any) -> None:
        """Asynchronously puts the break sentinel to all IO objects.

        Args:
            value: The object to put into this object.
            *args: The arguments for the inner io objects' put.
            **kwargs: The keyword arguments for the inner io objects' put.
        """
        await gather(
            *(io_object.put_async(self.break_sentinel, *args, **kwargs) for io_object in self.io_objects.values())
        )

    # Join
    def join_all(self, *args: Any, **kwargs: Any) -> None:
        for io_object in self.iter_visible_io_values():
            io_object.join(*args, **kwargs)

    async def join_all_async(self, *args: Any, **kwargs: Any) -> None:
        await gather(*(create_task(v.join_async(*args, **kwargs)) for v in self.iter_visible_io_values()))

    def join_groups(self, groups: Iterable[str] | str = "__default__", *args: Any, **kwargs: Any) -> None:
        """Joins the required IO objects.

        Args:
            groups: The names of the required groups IO objects to join.
            *args: Positional arguments passed to the `join` method of individual containers.
            **kwargs: Keyword arguments passed to the `join` method of individual containers.
        """
        ios = tuple(self.iter_groups_io_values(groups=groups))
        while any(r_io.poll() for r_io in ios):
            for r_io in ios:
                r_io.join(*args, **kwargs)

    async def join_groups_async(self, groups: Iterable[str] | str = "__default__", *args: Any, **kwargs: Any) -> None:
        """Asynchronously, joins the required IO objects.

        Args:
            groups: The names of the required groups IO objects to join.
            *args: Positional arguments passed to the `join` method of individual containers.
            **kwargs: Keyword arguments passed to the `join` method of individual containers.
        """
        ios = tuple(self.iter_groups_io_values(groups=groups))
        while any(await gather(*(r_io.poll_async() for r_io in ios))):
            await gather(*(create_task(r_io.join_async(*args, **kwargs)) for r_io in ios))

    # Tasks
    def join_tasks(self) -> None:
        """Joins all currently scheduled tasks."""
        for task in chain(self.get_tasks, self.put_tasks):
            while not task.done():
                pass

    async def join_tasks_async(self, timeout: float | None = None) -> None:
        """Asynchronously joins all currently scheduled tasks."""
        if timeout is None:
            await gather(*chain(self.get_tasks, self.put_tasks))
        else:
            await wait_for(gather(*chain(self.get_tasks, self.put_tasks)), timeout=timeout)

    def cancel_tasks(self) -> None:
        for task in chain(self.get_tasks, self.put_tasks):
            task.cancel()

    def stop(self) -> None:
        self.cancel_tasks()
        self.stop_listeners()
        self.callback_manager.cancel_tasks()

    async def stop_async(self, timeout: float | None = 1.0) -> None:
        try:
            await self.join_tasks_async(timeout=timeout)
        except TimeoutError:
            self.cancel_tasks()

        await self.stop_listeners_async(timeout=timeout)

        try:
            await self.callback_manager.join_tasks_async(timeout=timeout)
        except TimeoutError:
            self.callback_manager.cancel_tasks()

        tasks = deque()
        for io_ in self.encapsulated_routers.values():
            tasks.append(io_.stop_async(timeout=timeout))
        await gather(*tasks)

    # Encapsulated IO
    def encapsulate_io(self, io_: "IORouter") -> None:
        self.encapsulated_routers[io_.id_number] = io_
        io_.set_parent(self)

    def encapsulated_put(self, key, *arg: Any, **kwargs) -> None:
        self.encapsulated_wrappers[key].put(*arg, **kwargs)

    async def encapsulated_put_async(self, key: int, *arg: Any, **kwargs) -> None:
        await self.encapsulated_wrappers[key].put_async(*arg, **kwargs)

    def encapsulated_get(self, key, *args, **kwargs) -> Any:
        return self.encapsulated_wrappers[key].get(*args, **kwargs)

    async def encapsulated_get_async(self, key, *args, **kwargs) -> Any:
        return await self.encapsulated_wrappers[key].get_async(*args, **kwargs)

    def encapsulated_join(self, key, *args, **kwargs) -> None:
        self.encapsulated_wrappers[key].join(*args, **kwargs)

    async def encapsulated_join_async(self, key, *args, **kwargs) -> None:
        await self.encapsulated_wrappers[key].join_async(*args, **kwargs)

    def create_encapsulated_wrapper(self, key, io_, *args, **kwargs) -> IOWrapper:
        self.encapsulated_wrappers[key] = io_

        getter = partial(self.encapsulated_get, key, *args, **kwargs)
        getter_async = partial(self.encapsulated_get_async, key, *args, **kwargs)
        putter = partial(self.encapsulated_put, key, *args, **kwargs)
        putter_async = partial(self.encapsulated_put_async, key, *args, **kwargs)
        joiner = partial(self.encapsulated_join, key, *args, **kwargs)
        joiner_async = partial(self.encapsulated_join_async, key, *args, **kwargs)

        return IOWrapper(getter, getter_async, putter, putter_async, joiner, joiner_async)

    def create_io_wrapper_parent(
        self,
        key,
        *args: Any,
        e_args: Iterable[Any, ...] = (),
        e_kwargs: MutableMapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> BaseIO:
        io_ = self.create_io_wrapper(*args, **kwargs)
        return self._parent().create_encapsulated_wrapper(key, io_, *e_args, **(e_kwargs or {}))

    def provide_io_wrapper(
        self,
        key,
        *args: Any,
        e_args: Iterable[Any, ...] = (),
        e_kwargs: MutableMapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> BaseIO:
        io_ = self.create_io_wrapper(*args, **kwargs)
        if self.parent is not None:
            return self._parent().create_encapsulated_wrapper(key, io_, *e_args, **(e_kwargs or {}))
        else:
            return io_

    async def provide_io_wrapper_async(
        self,
        key: str | int,
        *args: Any,
        e_args: Iterable[Any, ...] = (),
        e_kwargs: MutableMapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> BaseIO:
        io_ = self.create_io_wrapper(*args, **kwargs)
        if self.parent is not None:
            return self._parent().create_encapsulated_wrapper(key, io_, *e_args, **(e_kwargs or {}))
        else:
            return io_

    # Linking
    def set_parent(self, io_: "IORouter") -> None:
        self._parent = ReferenceType(io_)

    def create_link_none(self, *args: Any, **kwargs: Any) -> None:
        return None

    def create_link_self(self, *args: Any, **kwargs: Any) -> BaseIO:
        return self

    def create_link_pass_io(self, name: str, *args: Any, **kwargs: Any) -> BaseIO:
        return self.io_objects[name]

    def create_link_wrapper(self, name: str, *args: Any, **kwargs: Any) -> BaseIO:
        return self.create_io_wrapper(name, *args, **kwargs)

    def create_link_parent(
        self,
        key,
        *args: Any,
        e_args: Iterable[Any, ...] = (),
        e_kwargs: MutableMapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> BaseIO:
        return self.create_io_wrapper_parent(key, *args, e_args=e_args, e_kwargs=e_kwargs, **kwargs)

    def link_forward(
        self,
        source: str,
        other: "IORouter",
        destination: str | None = None,
        *args: Any,
        encapsulate: bool = False,
        **kwargs: Any,
    ) -> None:
        """Establishes a forward link from this router to another IO object.

        This method creates a link between the `source` IO object in this router and the `other` IO object. If the
        `destination` is specified, the link is made with the IO object within the `other` object. If the link is
        identified as a listen link (where this router should listen for data from the `other` object),
        the `other` object is added to the scheduled listener links. Otherwise, if a `destination` is specified and
        a link IO object is created by the `other` router, it replaces the `source` IO object in this router.

        Args:
            source: The name of the source IO object in this router.
            other: The IO object to link to.
            destination: The name of the destination IO object in the `other` object. If `None`, the link is made
                         directly to the `other` object.
            *args: Additional positional arguments passed to the `create_link` method of the `other` object
                   if a destination is specified.
            **kwargs: Additional keyword arguments passed to the `create_link` method of the `other` object
                      if a destination is specified.
        """
        if self.io_objects.get(source, None) is None:
            raise KeyError(f"Source IO: {source} not found in {self.name}")
        if destination is not None and other.io_objects.get(destination, None) is None:
            raise KeyError(f"Destination IO: {destination} not found in {other.name}")

        key = (self.id_number, source, other.id_number, destination)
        self.links_to[key] = other
        other.links_from[key] = self

        if encapsulate:
            self.encapsulate_io(other)

        if destination is None:
            self.io_objects[source] = other
        elif other.parent is not None and (self.parent is not other.parent):
            self.io_objects[source] = other.create_link_parent(key, destination, *args, **kwargs)
        elif (d_io := other.create_link(destination, *args, **kwargs)) is not None:
            self.io_objects[source] = d_io

    def link_backward(
        self,
        other: "IORouter",
        source: str,
        destination: str | None = None,
        *args: Any,
        encapsulate: bool = False,
        **kwargs: Any,
    ) -> None:
        if other.io_objects.get(source, None) is None:
            raise KeyError(f"Source IO: {source} not found in {other.name}")
        if destination is not None and self.io_objects.get(destination, None) is None:
            raise KeyError(f"Destination IO: {destination} not found in {self.name}")

        key = (other.id_number, source, self.id_number, destination)
        other.links_to[key] = self
        self.links_from[key] = other

        if encapsulate:
            self.encapsulate_io(other)

        if destination is None:
            other.io_objects[destination] = self
        elif self.parent is not None and (self.parent is not other.parent):
            other.io_objects[destination] = self.create_link_parent(key, source, *args, **kwargs)
        elif (d_io := self.create_link(source, *args, **kwargs)) is not None:
            other.io_objects[destination] = d_io

    def get_links_from(self) -> dict[tuple[int, str, int, str], "IORouter"]:
        return self.links_from

    async def get_links_from_async(self) -> dict[tuple[int, str, int, str], "IORouter"]:
        return self.links_from

    def get_links_to(self) -> dict[tuple[int, str, int, str], "IORouter"]:
        return self.links_to

    async def get_links_to_async(self) -> dict[tuple[int, str, int, str], "IORouter"]:
        return self.links_to

    def get_links(self) -> dict[str, IOMap] | None:
        """Gets the links of this IO object.

       Returns:
           The links of this IO object.
       """
        return {n: m.generate_io_map() for n, m in self.iter_visible_io_items()}

    def get_link_endpoints(self, endpoints: dict | None = None, memo: set | None = None) -> dict["IORouter", Any]:
        if endpoints is None:
            endpoints = {}

        if memo is None:
            memo = set()

        if self.directly_linked:
            for next_io in self.directly_linked:
                if next_io not in memo:
                    memo.add(next_io)
                    next_io.get_link_endpoints(endpoints)
        else:
            for k, next_io in self.links_to.items():
                _, n, _, d = k
                if self.is_endpoint_link(self, next_io):
                    endpoints[k] = (self, n, next_io, d)
                elif self not in memo:
                    memo.add(self)
                    next_io.get_link_endpoints(endpoints)

        return endpoints

    # Listening
    def create_io_listen_container(
        self,
        name: str,
        type_: type[BaseIO] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if type_ is None:
            type_ = self.default_io_listen_container_type

        self.io_objects[name] = type_(*args, **kwargs)

    async def create_io_listen_container_async(
        self,
        name: str,
        type_: type[BaseIO] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if type_ is None:
            type_ = self.default_io_listen_container_type

        self.io_objects[name] = type_(*args, **kwargs)

    def register_listener_link_from(
        self,
        other: "IORouter",
        source: str,
        destination: str | None = None,
        create_container: bool = True,
    ) -> None:
        name = f"{other.name}:{source}_to_{self.name}{f':{destination}' if destination else ''}"

        if create_container:
            other.create_io_listen_container(name=source)

        self.listener_functions[name] = [
            other.provide_io_wrapper(name, source),
            self.provide_io_wrapper(name, destination)
        ]

    async def register_listener_link_from_async(
        self,
        other: "IORouter",
        source: str,
        destination: str | None = None,
        create_container: bool = True,
    ) -> None:
        name = f"{other.name}:{source}_to_{self.name}{f':{destination}' if destination else ''}"

        if create_container:
            await other.create_io_listen_container_async(name=source)

        self.listener_functions[name] = list(await gather(
            other.provide_io_wrapper_async(name, source),
            self.provide_io_wrapper_async(name, destination),
        ))

    def register_listener_links(self):
        for key, other in self.links_from.items():
            if self.is_listen_link(other, self):
                self.register_listener_link_from(other, key[1], key[3])

    async def register_listener_links_async(self):
        coros = deque()
        for key, other in self.links_from.items():
            if self.is_listen_link(other, self):
                coros.append(self.register_listener_link_from_async(other, key[1], key[3]))
        await gather(*coros)

    async def listen_get_put_functions_async(self, get: Callable, put: Callable) -> None:
        """Asynchronously listens for data from a get function and forwards it to a put function.

        Args:
            get: The get function to listen.
            put: The put function to forward to the get output to.
        """
        while self._is_listening:
            await put(await get())

    def start_listeners(self) -> None:
        if not self._is_listening:
            self._is_listening = True

        for name, (get, put) in self.listener_functions.items():
            if name not in self.listeners:
                task = create_task(self.listen_get_put_functions_async(get.getter_async, put.putter_async))
                self.listeners[name] = task
                task.add_done_callback(partial(self._remove_listener, name=name))

    async def start_listeners_async(self) -> None:
        self.start_listeners()

    def _remove_listener(self, task: Task, name: str) -> None:
        del self.listeners[name]

    def stop_listeners(self, msg: Any | None = None) -> None:
        self._is_listening = False

        for listener in self.listeners.values():
            listener.cancel(msg)

    async def stop_listeners_async(self, timeout: float | None = None, msg: Any | None = None) -> None:
        self._is_listening = False
        try:
            await wait_for(gather(*(shield(listener) for listener in self.listeners.values())), timeout=timeout)
        except TimeoutError:
            for listener in self.listeners.values():
                listener.cancel(msg)

    # Callback
    def register_io_callback(
        self,
        name: str,
        io_: BaseIO | None = None,
        callback: Callable | None = None,
        callback_async: Callable | None = None,
        get: str | None = None,
        get_async: str | None = None,
        put: str | None = None,
        put_async: str | None = None,
    ) -> None:
        if io_ is None:
            io_ = self.io_objects[name]

        if callback is None:
            if (callback := self.callback_manager.callbacks.get(name, None)) is None:
                if (scheduler := self.callback_manager.schedulers.get(name, None)) is None:
                    self.callback_manager.register_scheduler(name)
                    scheduler = self.callback_manager.schedulers[name]
                self.callback_manager.register_scheduler_callback(name, scheduler)
                callback = self.callback_manager.callbacks[name]
        else:
            self.callback_manager.register_callback(name, callback)

        if callback_async is None:
            if (callback_async := self.callback_manager.callbacks_async.get(name, None)) is None:
                if (scheduler := self.callback_manager.schedulers.get(name, None)) is None:
                    self.callback_manager.register_scheduler(name)
                    scheduler = self.callback_manager.schedulers[name]
                self.callback_manager.register_scheduler_callback(name, scheduler)
                callback_async = self.callback_manager.callbacks_async[name]
        else:
            self.callback_manager.register_callback(name, callback, is_async=True)

        self.io_objects[name] = IOCallbackWrapper(
            io_,
            callback,
            callback_async,
            get,
            get_async,
            put,
            put_async,
        )

    def map_conditional_callbacks_to_groups(
        self,
        groups: Iterable[str] | str | None,
        condition_names: Iterable[str],
    ) -> None:
        for name in self.iter_groups_io_keys(groups=groups):
            self.callback_manager.map_conditionals_to_group(name, condition_names)

    def create_groups_to_io_callback(
        self,
        groups: str | Iterable[str],
        io_name: str,
        callback: Callable | None = None,
        callback_async: Callable | None = None,
        cc_kwargs: dict[str, Any] | None = None,
        cc_async_kwargs: dict[str, Any] | None = None,
        defaults: dict[str, Any] | None = None,
        get: str | None = None,
        get_async: str | None = None,
        put: str | None = "after_put",
        put_async: str | None = "after_put_async",
        *,
        get_groups: str | Iterable[str] | None = None,
    )-> None:
        if get_groups is None:
            get_groups = groups

        if callback is None:
            callback = self.inputs_to_output

        if callback_async is None:
            callback_async = self.inputs_to_output_async

        conditional_callback_name = f"{str(groups)}_to_{io_name}"
        conditional_callback_async_name = f"{str(groups)}_to_{io_name}_async"
        conditional_callback_kwargs = {
            "name": conditional_callback_name,
            "callback_kwargs": {
                "callback": callback,
                "get_method": "get_groups",
                "get_kwargs": {"groups": get_groups, "defaults": (defaults or {})},
                "put_method": "put_item_value",
                "put_kwargs": {"name": io_name},
            },
            "condition_kwargs": {"method": "poll_groups", "groups": groups},
            "is_async": False,
        }
        conditional_callback_async_kwargs =  {
            "name": conditional_callback_async_name,
            "callback_kwargs": {
                "callback": callback_async,
                "get_method": "get_groups",
                "get_kwargs": {"groups": get_groups, "defaults": (defaults or {})},
                "put_method": "put_item_value_async",
                "put_kwargs": {"name": io_name},
            },
            "condition_kwargs": {"method": "poll_groups_async", "groups": groups},
            "is_async": True,
        }

        self.register_conditional_callback(**(conditional_callback_kwargs | (cc_kwargs or {})))
        self.register_conditional_callback(**(conditional_callback_async_kwargs | (cc_async_kwargs or {})))

        for name in self.iter_groups_io_keys(groups=groups):
            if not isinstance(self.io_objects[name], IOCallbackWrapper):
                self.register_io_callback(name, get=get, get_async=get_async, put=put, put_async=put_async)
            self.callback_manager.map_conditionals_to_scheduler(name, (conditional_callback_async_name, ))

    def create_ios_to_io_callback(
        self,
        ios: str | Iterable[str],
        io_name: str,
        callback: Callable | None = None,
        callback_async: Callable | None = None,
        cc_kwargs: dict[str, Any] | None = None,
        cc_async_kwargs: dict[str, Any] | None = None,
        defaults: dict[str, Any] | None = None,
        get: str | None = None,
        get_async: str | None = None,
        put: str | None = "after_put",
        put_async: str | None = "after_put_async",
        *,
        get_ios: str | Iterable[str] | None = None,
    )-> None:
        if get_ios is None:
            get_ios = ios

        if callback is None:
            callback = self.inputs_to_output

        if callback_async is None:
            callback_async = self.inputs_to_output_async

        conditional_callback_name = f"{str(ios)}_to_{io_name}"
        conditional_callback_async_name = f"{str(ios)}_to_{io_name}_async"
        conditional_callback_kwargs = {
            "name": conditional_callback_name,
            "callback_kwargs": {
                "callback": callback,
                "get_method": "get_items",
                "get_kwargs": {"names": get_ios, "defaults": (defaults or {})},
                "put_method": "put_item_value",
                "put_kwargs": {"name": io_name},
            },
            "condition_kwargs": {"method": "poll_all_ios", "names": ios},
            "is_async": False,
        }
        conditional_callback_async_kwargs =  {
            "name": conditional_callback_async_name,
            "callback_kwargs": {
                "callback": callback_async,
                "get_method": "get_items",
                "get_kwargs": {"names": get_ios, "defaults": (defaults or {})},
                "put_method": "put_item_value_async",
                "put_kwargs": {"name": io_name},
            },
            "condition_kwargs": {"method": "poll_all_ios_async", "names": ios},
            "is_async": True,
        }

        self.register_conditional_callback(**(conditional_callback_kwargs | (cc_kwargs or {})))
        self.register_conditional_callback(**(conditional_callback_async_kwargs | (cc_async_kwargs or {})))

        if isinstance(ios, str):
            ios = (ios,)

        for name in ios:
            if not isinstance(self.io_objects[name], IOCallbackWrapper):
                self.register_io_callback(name, get=get, get_async=get_async, put=put, put_async=put_async)
            self.callback_manager.map_conditionals_to_scheduler(name, (conditional_callback_async_name, ))

    # Routing Callback Method and Functions
    @staticmethod
    def inputs_to_output(inputs: dict) -> dict:
        return inputs

    @staticmethod
    async def inputs_to_output_async(inputs: dict) -> dict:
        return inputs
