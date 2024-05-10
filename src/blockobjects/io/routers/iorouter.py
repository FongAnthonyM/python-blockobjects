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
from asyncio import gather, create_task, Task, CancelledError
from asyncio.events import AbstractEventLoop, get_event_loop, _get_running_loop
from collections.abc import Iterable, Callable
from collections import deque
from functools import partial
from itertools import chain
from typing import ClassVar, Any
from types import MethodType
from weakref import WeakKeyDictionary, WeakSet

# Third-Party Packages #
from baseobjects import SentinelObject, search_sentinel
from baseobjects.collections import OrderableDict
from baseobjects.functions import MethodMultiplexer
import dill

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

    # IO
    default_io: type[BaseIO] = IOQueue
    required: tuple[str] = ()
    optional_defaults: dict[str, Any] = {}

    # Links
    create_link: MethodMultiplexer
    directly_linked: WeakSet
    links_to: dict[tuple[int, int, int, int], tuple[str, "IORouter", str]]
    links_from: dict[tuple[int, int, int, int], tuple[str, "IORouter", str]]
    endpoints: dict[tuple[int, int, int, int], tuple["IORouter", str, "IORouter", str]]
    endpoint_tasks: set[Task]

    # Get/Put Tasks
    wrapped_getter: str | None = None
    wrapped_getter_async: str | None = None
    wrapped_putter: str | None = "put_callback"
    wrapped_putter_async: str | None = "put_callback_async"
    get_tasks: set[Task]
    put_tasks: set[Task]

    # Listening
    _is_listening: bool = True
    scheduled_listener_links: set[tuple[int, int, int, int]]
    listeners: dict[tuple[int, int, int, int], Task]

    # Callback
    callback: Callable[[Any], None]
    callback_async: Callable[[Any], None]
    callback_executor: Task | None = None
    max_callback_tasks: int = 1
    callback_tasks: set[Task]

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
        self.optional_defaults = self.optional_defaults.copy()

        self.create_link = MethodMultiplexer(instance=self, select=self.default_create_link)
        self.directly_linked = WeakSet()
        self.links_to = {}
        self.links_from = {}
        self.endpoints = {}
        self.endpoint_tasks = set()

        self.get_tasks = set()
        self.put_tasks = set()

        self.scheduled_listener_links = set()
        self.listeners = dict()

        self.callback_tasks = set()

        # Parent Attributes #
        super().__init__()

        # Construction #
        if init:
            self.construct(io_, names, *args, **kwargs)

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

        for name in ("get_tasks", "put_tasks", "listeners", "callback_tasks", "directly_linked"):
            if name in state:
                del state[name]

        for name in ("callback", "callback_async"):
            if (m := state.get(name, None)) is not None and (_self_ := getattr(m, "_self_",  None)) is not None:
                del state[name]

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

    def is_remote(self) -> bool:
        return False

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

    def update_io(self, __m: Any = {}, /, **kwargs) -> None:
        """Updates this object's items. Nones are replaced with the default io type.

        Args:
            __m: A mapping with io objects which will replace items in this manager.
            **kwargs: Io objects which will replace items in this manager.
        """
        items = (kwargs if __m is None else (__m | kwargs))
        self.update({k: (self.default_io() if v is None else v) for k, v in items.items()})

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

    def get_deepest_io(self) -> dict:
        return {k: (v.get_deepest_io() if isinstance(v, IORouter) else v) for k, v in self.data.items()}

    def set_deepest_io(self, io_: dict[str, BaseIO | None]) -> None:
        for k, v in io_.items():
            if isinstance(v, dict):
                self.data[k].set_deepest_io(v)
            else:
                self.data[k] = v

    async def set_deepest_io_async(self, io_: dict[str, BaseIO | None]) -> None:
        for k, v in io_.items():
            if isinstance(v, dict):
                self.data[k].set_deepest_io(v)
            else:
                self.data[k] = v

    # Linking
    def create_link_none(self, *args: Any, **kwargs: Any) -> None:
        return None

    def create_link_self(self, *args: Any, **kwargs: Any) -> BaseIO:
        return self

    def create_link_pass_io(self, name: str, *args: Any, **kwargs: Any) -> BaseIO:
        return self.data[name]

    def link_forward(
        self,
        source: str,
        other: "IORouter",
        destination: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        key = (id(self), id(source), id(other), id(destination))
        self.links_to[key] = (source, other, destination)
        other.links_from[key] = (destination, self, source)
        if self.is_listen_link(self, other):
            other.scheduled_listener_links.add(key)
            if destination is None:
                self.data[source] = other
        else:
            if destination is None:
                self.data[source] = other
            elif (d_io := other.create_link(destination, *args, **kwargs)) is not None:
                self.data[source] = d_io

    def link_backward(
        self,
        other: "IORouter",
        source: str,
        destination: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        key = (id(other), id(source), id(self), id(destination))
        other.links_to[key] = (source, self, destination)
        self.links_from[key] = (destination, other, source)
        if self.is_listen_link(other, self):
            self.scheduled_listener_links.add(key)
            if destination is None:
                other.data[source] = self
        else:
            if destination is None:
                other.data[source] = self
            elif (d_io := self.create_link(destination, *args, **kwargs)) is not None:
                other.data[source] = d_io

    def get_links(self) -> dict[str, IOMap] | None:
        """Gets the links of this IO object.

       Returns:
           The links of this IO object.
       """
        return {n: m.generate_io_map() for n, m in self.data}

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
            for k, (n, next_io, d) in self.links_to.items():
                if self.is_endpoint_link(self, next_io):
                    endpoints[k] = (self, n, next_io, d)
                elif self not in memo:
                    memo.add(self)
                    next_io.get_link_endpoints(endpoints)

        return endpoints

    # Callback
    def set_callbacks(self, func, func_async) -> None:
        """Sets the callback functions.

        Args:
            func: The synchronous callback function.
            func_async: The asynchronous callback function.
        """
        self.callback = func
        self.callback_async = func_async

    async def set_callbacks_async(self, func, func_async) -> None:
        """Sets the callback functions.

        Args:
            func: The synchronous callback function.
            func_async: The asynchronous callback function.
        """
        self.callback = func
        self.callback_async = func_async

    def callback_condition(self, required: Iterable[str] | None = None, *args, **kwargs) -> bool:
        """Checks if all required IO objects are ready for a callback.

        Args:
            required: The names of the required IO objects. If None, defaults to self.required or self.order.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            True if all required IO objects are ready, False otherwise.
        """
        required = (self.required or self.order) if required is None else required
        return all(v.poll() for k, v in self.data.items() if k in required)

    async def callback_condition_async(self, required: Iterable[str] | None = None, *args, **kwargs) -> bool:
        """Asynchronously checks if all required IO objects are ready for a callback.

        Args:
            required: The names of the required IO objects. If None, defaults to self.required or self.order.
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            True if all required IO objects are ready, False otherwise.
        """
        required = (self.required or self.order) if required is None else required
        return all(v.poll() for k, v in self.data.items() if k in required)

    def _execute_next_callback(self, task, fut) -> None:
        """
        Executes the next callback if the callback condition is met.

        Args:
            task: The task that just completed.
            fut: The future object to set the result of the task.
        """
        self.callback_tasks.discard(task)
        if self.callback_condition():
            new_task = create_task(self.callback_async(self.get_required()))
            self.callback_tasks.add(new_task)
            # Have the new task remove its reference and run the next callback when it's done
            task.add_done_callback(partial(self._execute_next_callback, fut=fut))
        else:
            fut.set_result(None)

    def execute_callback(self, *args, **kwargs) -> None:
        """
        Executes the callback function while the callback condition is met.

        Args:
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.
        """
        while self.callback_condition():
            # Callback
            self.callback(self.get_required())

    async def execute_callback_async(self, *args, **kwargs) -> None:
        """
        Asynchronously executes the callback function while the callback condition is met.

        Args:
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.
        """
        # Create Callback Tasks
        task_futures = deque()
        for i in range(self.max_callback_tasks):
            if await self.callback_condition_async():
                # Create Execute Task
                task = create_task(self.callback_async(self.get_required()))
                self.callback_tasks.add(task)
                # Create Future
                fut = _get_running_loop().create_future()
                task_futures.append(fut)
                # Have the new task remove its reference and run the next callback when it's done
                task.add_done_callback(partial(self._execute_next_callback, fut=fut))

        # Wait for task futures
        await gather(*task_futures)

    def remove_executor(self, task):
        """
        Removes the executor task.

        Args:
            task: The task to be removed.
        """
        self.callback_executor = None

    def schedule_callback(self, *args, **kwargs) -> None:
        """
        Schedules the execution of the callback function.

        Args:
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.
        """
        self.execute_callback(*args, **kwargs)

    async def schedule_callback_async(self, *args, **kwargs) -> None:
        """Asynchronously schedules the execution of the callback function.

        This method checks if there's no currently executing callback and if the callback condition is met. If both
        conditions are true, it creates a new task to execute the callback function asynchronously.

        It also adds a done callback to the task to remove the executor when the task is done.

        Args:
            *args: Variable length argument list to be passed to the callback function.
            **kwargs: Arbitrary keyword arguments to be passed to the callback function.
        """
        if self.callback_executor is None and await self.callback_condition_async():
            self.callback_executor = create_task(self.execute_callback_async(*args, **kwargs))
            self.callback_executor.add_done_callback(self.remove_executor)

    def cancel_callbacks(self) -> None:
        for task in self.callback_tasks:
            task.cancel()

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
        task = create_task(self.data[name].get_async(name=name, **kwargs))
        self.get_tasks.add(task)
        task.add_done_callback(self.get_tasks.discard)
        return await task

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
        tasks = set
        for v in self.data.values():
            t = create_task(v.get_async(*args, **kwargs))
            tasks.add(t)
            t.add_done_callback(self.get_tasks.discard)
        self.get_tasks.update(tasks)
        return await gather(*tasks)

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
        name, io_, origin = self.links_from[key]
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
            self.callback(items)

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
        name, io_, origin = self.links_from[key]
        # Get as a task
        task = create_task(io_.get_async() if origin is None else io_.get_item_async(origin))
        self.get_tasks.add(task)
        task.add_done_callback(self.get_tasks.discard)
        # Put into self
        await self.data[name].put_async(await task, *args, **kwargs)
        required = set((self.required or self.order) if required is None else required)

        if all(v.poll() for k, v in self.data.items() if k in required):
            items = deque()
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
            task = create_task(self.callback_async(dict(zip(self.data.keys(), await gather(*items)))))
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
        tasks = deque()
        for v in self.data.values():
            t = create_task(v.get_async(*args, **kwargs))
            tasks.append(t)
            t.add_done_callback(self.get_tasks.discard)
        self.get_tasks.update(tasks)
        return dict(zip(self.data.keys(), await gather(*tasks)))

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

        tasks = deque()
        for k, v in self.data.items():
            if k in required:
                t = create_task(v.get_async(*args, **kwargs))
            else:
                t = create_task(v.get_async(
                    *args,
                    block=False,
                    default=defaults[k] if k in defaults else default,
                    **kwargs
                ))
            tasks.append(t)
            t.add_done_callback(self.get_tasks.discard)
        self.get_tasks.update(tasks)
        return dict(zip(self.data.keys(), await gather(*tasks)))

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
        await self.data[name].put_async(value, *args, **kwargs)

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

    def put_callback(
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
        # Put data into IO
        self.data[name].put(value, *args, **kwargs)

        # Schedule Callback
        required = set((self.required or self.order) if required is None else required)
        self.schedule_callback(required, default, defaults)

    async def put_callback_async(
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
        # Put data into IO
        await self.data[name].put_async(value, *args, **kwargs)

        # Schedule Callback
        required = set((self.required or self.order) if required is None else required)
        await self.schedule_callback_async(required, default, defaults)

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

    # Tasks
    def cancel_tasks(self) -> None:
        for task in chain(self.get_tasks, self.put_tasks):
            task.cancel()

    def stop(self) -> None:
        self.cancel_tasks()
        self.stop_listeners()
        self.cancel_callbacks()

    async def stop_async(self) -> None:
        self.cancel_tasks()
        self.stop_listeners()
        self.cancel_callbacks()

    # Listening
    async def listen_link_async(self, key: tuple[int, int, int, int], *args, **kwargs) -> None:
        """Put an item into an IO object.

        Args:
            name: The key name to the IO object to put the item into.
            value: The value to put in the IO object.
            *args: The arguments of the put of the IO object.
            **kwargs: The keyword arguments of the put of the IO object.
        """
        name, io_, origin = self.links_from[key]
        get_method = io_.get_async if origin is None else partial(io_.get_item_async, origin)

        while self._is_listening:
            await self.data[name].put_async(await get_method())
            await self.schedule_callback_async()

    def _remove_listener(self, task: Task, key: tuple[int, int, int, int]) -> None:
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
