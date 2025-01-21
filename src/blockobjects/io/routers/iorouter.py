""" iorouter.py
An IO object which maps inputs to outputs.
"""
from sqlalchemy.ext.mutable import MutableDict

# Package Header #
from ...header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Standard Libraries #
from asyncio import gather, create_task, Task, CancelledError
from asyncio.events import AbstractEventLoop, get_event_loop, _get_running_loop
from collections.abc import Iterable, Iterator, Callable, MutableMapping, Generator
from collections import deque, ChainMap
from functools import partial
from itertools import chain
from typing import ClassVar, Any
from types import FunctionType, MethodType
from uuid import uuid4
from weakref import WeakKeyDictionary, WeakSet, ReferenceType

# Third-Party Packages #
from baseobjects import SentinelObject, DEFAULTSENTINEL
from baseobjects.collections import OrderableDict
from baseobjects.functions import MethodMultiplexer
from baseobjects.objects import CallbackManager

# Local Packages #
from ...process import AsyncQueue
from ..base import IOMap, BaseIO, BaseIOMultiplexer, IOForwarder, IOWrapper


# Definitions #
# Typing
IOGroupType = MutableMapping[str | int, BaseIO ]
IOGroupTypeMap = MutableMapping[str, IOGroupType]

# Classes #
class IORouter(BaseIOMultiplexer):
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
    default_join: ClassVar[str] = "join_groups"
    default_join_async: ClassVar[str] = "join_groups_async"
    default_create_link: ClassVar[str] = "create_link_pass_io"

    # Class Methods #
    @classmethod
    def is_endpoint_link(cls, source: "IORouter", destination: "IORouter") -> bool:
        return source.is_remote() and not destination.is_remote()

    @classmethod
    def is_listen_link(cls, source: "IORouter", destination: "IORouter") -> bool:
        return cls.is_endpoint_link(source, destination)

    # Attributes #
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

    # Callbacks
    callback_manager: CallbackManager

    # IO
    hidden_groups: set[str] = {"encapsulated"}
    _visible_groups: set[str] | None = None
    default_io_type: type[BaseIO] = AsyncQueue
    default_values: dict[str, dict[str, Any]] = {}

    io_objects: ChainMap[str | int, BaseIO]
    io_groups: IOGroupTypeMap

    # Get/Put Tasks
    wrapped_getter: str | None = None
    wrapped_getter_async: str | None = None
    wrapped_putter: str | None = "put_callback"
    wrapped_putter_async: str | None = "put_callback_async"
    get_tasks: set[Task]
    put_tasks: set[Task]

    # Listening
    _is_listening: bool = True
    scheduled_listener_links: set[tuple[int, str, int, str]]
    listeners: dict[tuple[int, str, int, str], Task]

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

    @property
    def encapsulated(self) -> MutableMapping[int, BaseIO]:
        return self.io_groups["encapsulated"]

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        io_: IOGroupTypeMap | MutableMapping[str, Iterable[str | int]] | Iterable[str | int] | None = None,
        visible_groups: Iterable[str] | None | SentinelObject = DEFAULTSENTINEL,
        hidden_groups: Iterable[str] | None = None,
        *args: Any,
        init: bool = True,
        **kwargs: Any,
    ) -> None:
        # Attributes #
        self.default_values = self.default_values.copy()

        self.id_number = uuid4().int
        self.create_link = MethodMultiplexer(instance=self, select=self.default_create_link)
        self.directly_linked = WeakSet()
        self.links_to = {}
        self.links_from = {}
        self.endpoints = {}
        self.endpoint_tasks = set()

        self.callback_manager = CallbackManager()

        self.hidden_groups = self.hidden_groups.copy()
        if self._visible_groups is not None:
            self.visible_groups = self.visible_groups.copy()

        __default__ = OrderableDict()
        encapsulated = OrderableDict()
        self.io_objects = ChainMap(__default__, encapsulated)
        self.io_groups = {"__default__": __default__, "encapsulated": encapsulated}

        self.get_tasks = set()
        self.put_tasks = set()

        self.scheduled_listener_links = set()
        self.listeners = dict()

        # Parent Attributes #
        super().__init__()

        # Construction #
        if init:
            self.construct(io_, visible_groups, *args, **kwargs)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}>"

    # Pickling
    def __getstate__(self) -> dict[str, Any]:
        """Creates a dictionary of attributes which can be used to rebuild this object.

        Returns:
            A dictionary of this object's attributes.
        """
        state = super().__getstate__()
        if (directly_linked := state.get("directly_linked", None)) is not None:
            state["directly_linked"] = set(directly_linked)

        for name in ("get_tasks", "put_tasks", "listeners", "callback_tasks", "directly_linked", "_parent"):
            if name in state:
                del state[name]

        # for name in ("callback", "callback_async", ):
        #     if (m := state.get(name, None)) is not None and (_self_ := getattr(m, "_self_",  None)) is not None:
        #         del state[name]

        return state

    def __setstate__(self, state: dict[str, Any]) -> None:
        """Builds this object based on a dictionary of corresponding attributes.

        Args:
            state: The attributes to build this object from.
        """
        super().__setstate__(state)
        self.get_tasks = set()
        self.put_tasks = set()
        self.listeners = dict()
        self.callback_tasks = set()
        self.directly_linked = WeakSet(state.get("directly_linked", None))
        for en in self.encapsulated.values():
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

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        io_: IOGroupTypeMap | MutableMapping[str, Iterable[str | int]] | Iterable[str | int] | None = None,
        visible_groups: Iterable[str] | None | SentinelObject = DEFAULTSENTINEL,
        hidden_groups: Iterable[str] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Constructs this object.

        Args:
            io_: The input/outputs to be managed.
            *args: Arguments for inheritance.
            **kwargs: Keyword arguments for inheritance.
        """
        if isinstance(io_, MutableMapping):
            if isinstance(next(iter(io_.values())), MutableMapping):
                self.require_io_groups(io_)
            else:
                self.create_ios(groups=io_)
        elif isinstance(io_, str):
            self.create_io(io_)
        else:
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
        return all(self.io_objects[n] for n in names)

    async def poll_all_ios_async(self, names: Iterable[str]) -> bool:
        """Asynchronously, checks if all given IO objects in this object have an item in them.

        Returns:
             Returns True if al the IO objects have an item in them, False otherwise.
        """
        return all(self.io_objects[n] for n in names)

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
        return False

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
            self.io_groups[group] = g = OrderableDict(name=io_)
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
                self.io_groups[group] = g = OrderableDict(ios)
                self.io_objects.maps.append(g)
            else:
                g.update(ios)

        return new_groups

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

    def get_deepest(self) -> dict:
        return {k: (v.get_deepest() if isinstance(v, IORouter) else v) for k, v in self.iter_visible_io_items()}

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

    def set_recursive(self, keys: tuple[str, ...], io_: BaseIO) -> None:
        if len(keys) == 1:
            self.io_objects[keys[0]] = io_
        else:
            self.io_objects[keys[0]].set_recursive(keys[1:], io_)

    async def set_recursive_async(self, keys: tuple[str, ...], io_: BaseIO) -> None:
        if len(keys) == 1:
            self.io_objects[keys[0]] = io_
        else:
            await self.io_objects[keys[0]].set_recursive_async(keys[1:], io_)

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

    # Encapsulated IO
    def encapsulate_io(self, io_: "IORouter") -> None:
        self.io_groups["encapsulated"][io_.id_number] = io_
        io_.set_parent(self)

    def encapsulated_put(self, id_: int, value: Any, *arg: Any, **kwargs) -> None:
        self.io_groups["encapsulated"][id_].put(value, *arg, **kwargs)

    async def encapsulated_put_async(self, id_: int, value: Any, *arg: Any, **kwargs) -> None:
        await self.io_groups["encapsulated"][id_].put_async(value, *arg, **kwargs)

    def encapsulated_get(self, id_: int, *args, **kwargs) -> Any:
        return self.io_groups["encapsulated"][id_].get( *args, **kwargs)

    async def encapsulated_get_async(self, id_: int, *args, **kwargs) -> Any:
        return await self.io_groups["encapsulated"][id_].get_async(*args, **kwargs)

    def encapsulated_join(self, id_: int, *args, **kwargs) -> None:
        self.io_groups["encapsulated"][id_].join(*args, **kwargs)

    async def encapsulated_join_async(self, id_: int, *args, **kwargs) -> None:
        await self.io_groups["encapsulated"][id_].join_async(*args, **kwargs)

    def create_encapsulated_wrapper(self, id_: int, *args, **kwargs) -> IOWrapper:
        getter = partial(self.encapsulated_get, id_)
        getter_async = partial(self.encapsulated_get_async, id_)
        putter = partial(self.encapsulated_put, id_)
        putter_async = partial(self.encapsulated_put_async, id_)
        joiner = partial(self.encapsulated_join, id_)
        joiner_async = partial(self.encapsulated_join_async, id_)

        return IOWrapper(getter, getter_async, putter, putter_async, joiner, joiner_async)

    # Linking
    def set_parent(self, io_: "IORouter") -> None:
        self._parent = ReferenceType(io_)
        self.create_link.select("create_link_parent")

    def create_link_none(self, *args: Any, **kwargs: Any) -> None:
        return None

    def create_link_self(self, *args: Any, **kwargs: Any) -> BaseIO:
        return self

    def create_link_pass_io(self, name: str, *args: Any, **kwargs: Any) -> BaseIO:
        return self.io_objects[name]

    def create_link_parent(self, *args: Any, **kwargs: Any):
        return self._parent().create_encapsulated_wrapper(*args, **kwargs)

    def link_forward(
        self,
        source: str,
        other: "IORouter",
        destination: str | None = None,
        *args: Any,
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
        key = (self.id_number, source, other.id_number, destination)
        self.links_to[key] = other
        other.links_from[key] = self
        if self.is_listen_link(self, other):
            other.scheduled_listener_links.add(key)
            if destination is None:
                self.io_objects[source] = other
        else:
            if destination is None:
                self.io_objects[source] = other
            elif other.parent is not None and (self.parent is not other.parent):
                self.io_objects[source] = other.create_link_parent(source, *args, **kwargs)
            elif (d_io := other.create_link(destination, *args, **kwargs)) is not None:
                self.io_objects[source] = d_io

    def link_backward(
        self,
        other: "IORouter",
        source: str,
        destination: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        key = (other.id_number, source, self.id_number, destination)
        other.links_to[key] = self
        self.links_from[key] = other
        if self.is_listen_link(other, self):
            self.scheduled_listener_links.add(key)
            if destination is None:
                other.io_objects[source] = self
        else:
            if destination is None:
                other.io_objects[source] = self
            elif self.parent is not None and (self.parent is not other.parent):
                other.io_objects[source] = self.create_link_parent(source, *args, **kwargs)
            elif (d_io := self.create_link(destination, *args, **kwargs)) is not None:
                other.io_objects[source] = d_io

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

    # Callback Conditions
    def create_condition_wrapper(
        self,
        method: str = "poll_groups",
        *args: Any,
        **kwargs: Any,
    ) -> Callable:
        # Build condition wrapper pieces
        condition_method = getattr(self, method)

        # Create callback wrapper
        def condition_wrapper(*a: Any, **k:Any) -> bool:
            return condition_method(**(kwargs | k))

        # Return callback wrapper
        return condition_wrapper

    def create_async_condition_wrapper(
        self,
        method: str = "poll_groups_async",
        *args: Any,
        **kwargs: Any,
    ) -> Callable:
        # Build condition wrapper pieces
        condition_method = getattr(self, method)

        # Create callback wrapper
        async def condition_wrapper(*a: Any, **k:Any) -> bool:
            return await condition_method(**(kwargs | k))

        # Return callback wrapper
        return condition_wrapper

    # Callbacks
    def create_callback_wrapper(
        self,
        callback: Callable,
        get_method: str = "get",
        callback_kwargs: dict[str, Any] | None = None,
        get_kwargs: dict[str, Any] | None = None,
        *args: Any,
        as_first: bool = False,
        **kwargs: Any,
    ) -> Callable:
        # Build callback wrapper pieces
        get_method_ = partial(getattr(self, get_method), **(get_kwargs or {}))
        c_kwargs = callback_kwargs or {}

        # Create callback wrapper
        if as_first:
            def callback_wrapper(*a: Any, **k:Any) -> None:
                callback(get_method_(), **(c_kwargs | k))
        else:
            def callback_wrapper(*a: Any, **k:Any) -> None:
                callback(**(get_method_() | (c_kwargs | k)))

        # Return callback wrapper
        return callback_wrapper

    def create_async_callback_wrapper(
        self,
        callback: Callable,
        get_method: str = "get_async",
        callback_kwargs: dict[str, Any] | None = None,
        get_kwargs: dict[str, Any] | None = None,
        *args: Any,
        as_first: bool = False,
        as_task: bool = False,
        **kwargs: Any,
    ) -> Callable:
        # Build callback wrapper pieces
        get_method_ = partial(getattr(self, get_method), **(get_kwargs or {}))
        c_kwargs = callback_kwargs or {}

        # Create callback wrapper
        if not as_first and not as_task:
            async def callback_wrapper(*a: Any, **k: Any) -> None:
                await callback(**(await get_method_() | (c_kwargs | k)))
        elif not as_first and as_task:
            async def callback_wrapper(*a: Any, **k: Any) -> Task:
                return create_task(callback(**(await get_method_() | (c_kwargs | k))))
        elif as_first and not as_task:
            async def callback_wrapper(*a: Any, **k: Any) -> None:
                await callback(await get_method_(), **(c_kwargs | k))
        else:
            async def callback_wrapper(*a: Any, **k: Any) -> Task:
                return create_task(callback(await get_method_(), **(c_kwargs | k)))

        # Return callback wrapper
        return callback_wrapper

    def create_routing_callback_wrapper(
        self,
        callback: Callable,
        get_method: str = "get",
        put_method: str = "put",
        callback_kwargs: dict[str, Any] | None = None,
        get_kwargs: dict[str, Any] | None = None,
        put_kwargs: dict[str, Any] | None = None,
        *args: Any,
        as_first: bool = False,
        **kwargs: Any,
    ) -> Callable:
        # Build callback wrapper pieces
        get_method_ = partial(getattr(self, get_method), **(get_kwargs or {}))
        put_method_ = partial(getattr(self, put_method), **(put_kwargs or {}))
        c_kwargs = callback_kwargs or {}

        # Create callback wrapper
        if as_first:
            def callback_wrapper(*a: Any, **k:Any) -> None:
                put_method_(callback(get_method_(), **(c_kwargs | k)))
        else:
            def callback_wrapper(*a: Any, **k:Any) -> None:
                put_method_(callback(**(get_method_() | (c_kwargs | k))))

        # Return callback wrapper
        return callback_wrapper

    def create_async_routing_callback_wrapper(
        self,
        callback: Callable,
        get_method: str = "get_async",
        put_method: str = "put_async",
        callback_kwargs: dict[str, Any] | None = None,
        get_kwargs: dict[str, Any] | None = None,
        put_kwargs: dict[str, Any] | None = None,
        *args: Any,
        as_first: bool = False,
        as_task: bool = False,
        **kwargs: Any,
    ) -> Callable:
        # Build callback wrapper pieces
        get_method_ = partial(getattr(self, get_method), **(get_kwargs or {}))
        put_method_ = partial(getattr(self, put_method), **(put_kwargs or {}))
        c_kwargs = callback_kwargs or {}

        # Create callback wrapper
        if not as_first and not as_task:
            async def callback_wrapper(*a: Any, **k: Any) -> None:
                await put_method_(await callback(**(await get_method_() | (c_kwargs | k))))
        elif not as_first and as_task:
            async def callback_wrapper(*a: Any, **k: Any) -> Task:
                return create_task(put_method_(create_task(callback(**(await get_method_() | (c_kwargs | k))))))
        elif as_first and not as_task:
            async def callback_wrapper(*a: Any, **k: Any) -> None:
                await put_method_(await callback(await get_method_(), **(c_kwargs | k)))
        else:
            async def callback_wrapper(*a: Any, **k: Any) -> Task:
                return create_task(put_method_(create_task(callback(await get_method_(), **(c_kwargs | k)))))

        # Return callback wrapper
        return callback_wrapper

    # Callback Management
    def register_callback(
        self,
        callback: tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]] | None = None,
        callback_async: tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]] | None = None,
    ) -> None:
        c_manager = self.callback_manager
        if callback is not None:
            call_method = self.create_callback_wrapper(**callback[1])
            cond_method = self.create_condition_wrapper(**callback[2])
            c_manager.callbacks[callback[0]] = c_manager.format_callback(
                callback=call_method,
                condition=cond_method,
                **callback[3],
            )
        if callback_async is not None:
            call_method = self.create_async_callback_wrapper(**callback_async[1])
            cond_method = self.create_async_condition_wrapper(**callback_async[2])
            c_manager.callbacks_async[callback_async[0]] = c_manager.format_callback(
                callback=call_method,
                condition=cond_method,
                **callback_async[3],
            )

    async def register_callback_async(
        self,
        callback: tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]] | None = None,
        callback_async: tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]] | None = None,
    ) -> None:
        c_manager = self.callback_manager
        if callback is not None:
            call_method = self.create_callback_wrapper(**callback[1])
            cond_method = self.create_condition_wrapper(**callback[2])
            c_manager.callbacks[callback[0]] = c_manager.format_callback(
                callback=call_method,
                condition=cond_method,
                **callback[3],
            )
        if callback_async is not None:
            call_method = self.create_async_callback_wrapper(**callback_async[1])
            cond_method = self.create_async_condition_wrapper(**callback_async[2])
            c_manager.callbacks_async[callback_async[0]] = c_manager.format_callback(
                callback=call_method,
                condition=cond_method,
                **callback_async[3],
            )

    def register_callbacks(
        self,
        callbacks: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
        callbacks_async: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
    ) -> None:
        c_manager = self.callback_manager
        if callbacks is not None:
            c_manager.callbacks.update((
                (n, c_manager.format_callback(
                    self.create_callback_wrapper(**call),
                    self.create_condition_wrapper(**cond),
                    **kw,
                ))
                for n, (call, cond, kw) in callbacks.items()
            ))
        if callbacks_async is not None:
            c_manager.callbacks_async.update((
                (n, c_manager.format_callback(
                    self.create_async_callback_wrapper(**call),
                    self.create_async_condition_wrapper(**cond),
                    **kw,
                ))
                for n, (call, cond, kw) in callbacks_async.items()
            ))

    async def register_callbacks_async(
        self,
        callbacks: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
        callbacks_async: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
    ) -> None:
        c_manager = self.callback_manager
        if callbacks is not None:
            c_manager.callbacks.update((
                (n, c_manager.format_callback(
                    self.create_callback_wrapper(**call),
                    self.create_condition_wrapper(**cond),
                    **kw,
                ))
                for n, (call, cond, kw) in callbacks.items()
            ))
        if callbacks_async is not None:
            c_manager.callbacks_async.update((
                (n, c_manager.format_callback(
                    self.create_async_callback_wrapper(**call),
                    self.create_async_condition_wrapper(**cond),
                    **kw,
                ))
                for n, (call, cond, kw) in callbacks_async.items()
            ))

    def _register_inner_callbacks(
        self,
        names: Iterator[str],
        callbacks: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
        callbacks_async: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
    ) -> None:
        try:
            name = next(names)
        except StopIteration:
            self.register_callbacks(callbacks, callbacks_async)
        else:
            self.io_objects[name]._register_inner_callbacks(names, callbacks, callbacks_async)

    def register_inner_callbacks(
        self,
        names: Iterable[str] | str,
        callbacks: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
        callbacks_async: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
    ) -> None:
        if isinstance(names, str):
            self.io_objects[names].register_callbacks(callbacks=callbacks, callbacks_async=callbacks_async)
        else:
            self._register_inner_callbacks(iter(names), callbacks, callbacks_async)

    async def _register_inner_callbacks_async(
        self,
        names: Iterator[str],
        callbacks: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
        callbacks_async: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
    ) -> None:
        try:
            name = next(names)
        except StopIteration:
            await self.register_callbacks_async(callbacks, callbacks_async)
        else:
            await self.io_objects[name]._register_inner_callbacks_async(names, callbacks, callbacks_async)

    async def register_inner_callbacks_async(
        self,
        names: Iterable[str] | str,
        callbacks: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
        callbacks_async: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
    ) -> None:
        if isinstance(names, str):
            await self.io_objects[names].register_callbacks_async(callbacks=callbacks, callbacks_async=callbacks_async)
        else:
            await self._register_inner_callbacks_async(iter(names), callbacks, callbacks_async)

    def register_routing_callback(
        self,
        callback: tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]] | None = None,
        callback_async: tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]] | None = None,
    ) -> None:
        c_manager = self.callback_manager
        if callback is not None:
            call_method = self.create_routing_callback_wrapper(**callback[1])
            cond_method = self.create_condition_wrapper(**callback[2])
            c_manager.callbacks[callback[0]] = c_manager.format_callback(
                callback=call_method,
                condition=cond_method,
                **callback[3],
            )
        if callback_async is not None:
            call_method = self.create_async_routing_callback_wrapper(**callback_async[1])
            cond_method = self.create_async_condition_wrapper(**callback_async[2])
            c_manager.callbacks[callback_async[0]] = c_manager.format_callback(
                callback=call_method,
                condition=cond_method,
                **callback_async[3],
            )

    async def register_routing_callback_async(
        self,
        callback: tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]] | None = None,
        callback_async: tuple[str, dict[str, Any], dict[str, Any], dict[str, Any]] | None = None,
    ) -> None:
        c_manager = self.callback_manager
        if callback is not None:
            call_method = self.create_routing_callback_wrapper(**callback[1])
            cond_method = self.create_condition_wrapper(**callback[2])
            c_manager.callbacks[callback[0]] = c_manager.format_callback(
                callback=call_method,
                condition=cond_method,
                **callback[3],
            )
        if callback_async is not None:
            call_method = self.create_async_routing_callback_wrapper(**callback_async[1])
            cond_method = self.create_async_condition_wrapper(**callback_async[2])
            c_manager.callbacks[callback_async[0]] = c_manager.format_callback(
                callback=call_method,
                condition=cond_method,
                **callback_async[3],
            )

    def register_routing_callbacks(
        self,
        callbacks: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
        callbacks_async: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
    ) -> None:
        c_manager = self.callback_manager
        if callbacks is not None:
            c_manager.callbacks.update((
                (n, c_manager.format_callback(
                    self.create_routing_callback_wrapper(**call),
                    self.create_condition_wrapper(**cond),
                    **kw,
                ))
                for n, (call, cond, kw) in callbacks.items()
            ))
        if callbacks_async is not None:
            c_manager.callbacks_async.update((
                (n, c_manager.format_callback(
                    self.create_async_routing_callback_wrapper(**call),
                    self.create_async_condition_wrapper(**cond),
                    **kw,
                ))
                for n, (call, cond, kw) in callbacks_async.items()
            ))

    async def register_routing_callbacks_async(
        self,
        callbacks: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
        callbacks_async: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
    ) -> None:
        c_manager = self.callback_manager
        if callbacks is not None:
            c_manager.callbacks.update((
                (n, c_manager.format_callback(
                    self.create_routing_callback_wrapper(**call),
                    self.create_condition_wrapper(**cond),
                    **kw,
                ))
                for n, (call, cond, kw) in callbacks.items()
            ))
        if callbacks_async is not None:
            c_manager.callbacks_async.update((
                (n, c_manager.format_callback(
                    self.create_async_routing_callback_wrapper(**call),
                    self.create_async_condition_wrapper(**cond),
                    **kw,
                ))
                for n, (call, cond, kw) in callbacks_async.items()
            ))

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
        d = dict(zip(keys, await gather(*tasks)))
        return d

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

    def put_item_callback(self, name: str, value: Any, *args: Any, **kwargs: Any) -> None:
        """Puts an item into an IO object and schedule a callback.

        Args:
            name: The key name to the IO object to put the item into.
            value: The value to put in the IO object.
            *args: The arguments of the put of the IO object.
            **kwargs: The keyword arguments of the put of the IO object.
        """
        # Put data into IO
        self.io_objects[name].put(value, *args, **kwargs)

        # Schedule Callback
        self.callback_manager.start_scheduler()

    async def put_item_callback_async(self, name: str, value: Any, *args: Any, **kwargs: Any) -> None:
        """Put an item into an IO object.

        Args:
            name: The key name to the IO object to put the item into.
            value: The value to put in the IO object.
            *args: The arguments of the put of the IO object.
            **kwargs: The keyword arguments of the put of the IO object.
        """
        # Put data into IO
        await self.io_objects[name].put_async(value, *args, **kwargs)

        # Schedule Callback
        self.callback_manager.start_scheduler()

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
        for io_object in self.io_objects.values():
            io_object.join(*args, **kwargs)

    async def join_all_async(self, *args: Any, **kwargs: Any) -> None:
        await gather(*(create_task(v.join_async(*args, **kwargs)) for v in self.io_objects.values()))

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
    def cancel_tasks(self) -> None:
        for task in chain(self.get_tasks, self.put_tasks):
            task.cancel()

    def stop(self) -> None:
        self.cancel_tasks()
        self.stop_listeners()
        self.callback_manager.cancel_tasks()

    async def stop_async(self) -> None:
        self.cancel_tasks()
        self.stop_listeners()
        self.callback_manager.cancel_tasks()

    # Listening
    async def listen_link_async(self, key: tuple[int, str, int, str], *args, **kwargs) -> None:
        """Asynchronously listens for data from a linked IO and forwards it to the current IO's data queue.

        This method continuously listens for data from a linked IO object based on the provided key. Once data is
        received, it is put into the current IO's data queue. Additionally, any scheduled callbacks are executed
        after putting data into the queue. This process repeats as long as the `_is_listening` flag is set to True.

        Args:
            key: A tuple containing the identifiers for the linked IO. The structure is (int, str, int, str) where
                 the elements represent unique identifiers and names for the origin and destination IOs.
            *args: Arguments which may be specified in an overriding method.
            **kwargs: Keyword arguments which may be specified in an overriding method.
        """
        _, origin, _, name = key
        io_ = self.links_from[key]
        # Determine the appropriate get method based on whether the origin is specified.
        get_method = io_.get_async if origin is None else partial(io_.get_item_async, origin)

        while self._is_listening:
            # Retrieve data from the linked IO and put it into the current IO's data queue.
            await self.io_objects[name].put_async(await get_method())
            # Start callback scheduler
            self.callback_manager.start_scheduler()

    def _remove_listener(self, task: Task, key: tuple[int, str, int, str]) -> None:
        del self.listeners[key]

    def start_listeners(self) -> None:
        if not self._is_listening:
            self._is_listening = True
        for key in self.scheduled_listener_links:
            if key not in self.listeners:
                self.listeners[key] = create_task(self.listen_link_async(key))

    async def start_listeners_async(self) -> None:
        if not self._is_listening:
            self._is_listening = True
        for key in self.scheduled_listener_links:
            if key not in self.listeners:
                self.listeners[key] = create_task(self.listen_link_async(key))

    def stop_listeners(self, msg: Any | None = None) -> None:
        self._is_listening = False
        for listener in self.listeners.values():
            listener.cancel(msg)

        self.listeners.clear()
