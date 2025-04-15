""" cycleiorouter.py.py

"""
# Header #
__package_name__ = "blockobjects"

__author__ = "Anthony Fong"
__credits__ = ["Anthony Fong"]
__copyright__ = "Copyright 2022, Anthony Fong"
__license__ = "MIT"

__version__ = "0.1.0"


# Imports #
# Standard Libraries #
from asyncio import create_task
from itertools import cycle
from typing import ClassVar, Any, Iterable, MutableMapping

# Third-Party Packages #
from baseobjects import SentinelObject, DEFAULTSENTINEL

# Local Packages #
from ..base import BaseIO
from .iorouter import IOGroupTypeMap, IORouter


# Definitions #
# Classes #
class CycleIORouter(IORouter):
    """An IO object which cycles through its inputs and outputs."""

    # Class Attributes #
    default_get: ClassVar[str] = "get_cycle"
    default_get_async: ClassVar[str] = "get_cycle_async"
    default_put: ClassVar[str] = "put_cycle"
    default_put_async: ClassVar[str] = "put_cycle_async"

    # Attributes #
    _get_cycle_order: tuple[str, ...] = ()
    _put_cycle_order: tuple[str, ...] = ()
    _get_cycle_iter: cycle
    _put_cycle_iter: cycle

    # Properties #
    @property
    def get_cycle_order(self) -> tuple[str, ...]:
        """The order in which the get methods will be cycled through."""
        return self._get_cycle_order

    @property
    def put_cycle_order(self) -> tuple[str, ...]:
        """The order in which the put methods will be cycled through."""
        return self._put_cycle_order

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        io_: IOGroupTypeMap | MutableMapping[str, Iterable[str | int]] | Iterable[str | int] | None = None,
        get_cycle_order: Iterable[str] | None = None,
        put_cycle_order: Iterable[str] | None = None,
        visible_groups: Iterable[str] | None | SentinelObject = DEFAULTSENTINEL,
        hidden_groups: Iterable[str] | None = None,
        *args: Any,
        name: str | None = None,
        default_io_type: type[BaseIO] | None = None,
        init: bool = True,
        **kwargs: Any,
    ) -> None:
        # Parent Attributes #
        super().__init__(name=name, init=False)

        # Construct #
        if init:
            self.construct(
                io_,
                get_cycle_order,
                put_cycle_order,
                visible_groups,
                hidden_groups,
                *args,
                default_io_type=default_io_type,
                **kwargs,
            )

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        io_: IOGroupTypeMap | MutableMapping[str, Iterable[str | int]] | Iterable[str | int] | None = None,
        get_cycle_order: Iterable[str] | None = None,
        put_cycle_order: Iterable[str] | None = None,
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
        if get_cycle_order is not None:
            self._get_cycle_order = tuple(get_cycle_order)

        if put_cycle_order is not None:
            self._put_cycle_order = tuple(put_cycle_order)

        self.build_cycle_iters()

        super().construct(
            io_,
            visible_groups,
            hidden_groups,
            *args,
            default_io_type=default_io_type,
            **kwargs,
        )

    # Cycle
    def build_cycle_iters(self) -> None:
        """Cycles through the IO objects."""
        self._get_cycle_iter = cycle(self.get_cycle_order)
        self._put_cycle_iter = cycle(self.put_cycle_order)

    def set_get_cycle_order(self, cycle_order: Iterable[str]) -> None:
        self._get_cycle_order = tuple(cycle_order)
        self._get_cycle_iter = cycle(self._get_cycle_order)

    def set_put_cycle_order(self, cycle_order: Iterable[str]) -> None:
        self._put_cycle_order = tuple(cycle_order)
        self._put_cycle_iter = cycle(self._put_cycle_order)

    # Get
    def get_cycle(self, *args: Any, **kwargs: Any) -> Any:
        """Gets an item from the IO objects in a cycled manner."""
        return self.io_objects[next(self._get_cycle_iter)].get(*args, **kwargs)

    async def get_cycle_async(self, *args: Any, **kwargs: Any) -> Any:
        """Gets an item from the IO objects in a cycled manner asynchronously."""
        task = create_task(self.io_objects[next(self._get_cycle_iter)].get_async(*args, **kwargs))
        self.get_tasks.add(task)
        task.add_done_callback(self.get_tasks.discard)
        return await task

    # Put
    def put_cycle(self, value: Any, *args: Any, **kwargs: Any) -> None:
        """Puts an item into the IO objects in a cycled manner."""
        self.io_objects[next(self._put_cycle_iter)].put(value, *args, **kwargs)

    async def put_cycle_async(self, value: Any, *args: Any, **kwargs: Any) -> None:
        """Puts an item into the IO objects in a cycled manner asynchronously."""
        task = create_task(self.io_objects[next(self._put_cycle_iter)].put_async(value, *args, **kwargs))
        self.put_tasks.add(task)
        task.add_done_callback(self.put_tasks.discard)
        return await task
