""" iocallbackwrapper.py.py

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
from asyncio import Task, create_task, gather
from collections.abc import Callable
from typing import ClassVar, Any

# Third-Party Packages #

# Local Packages #
from ..base import BaseIO, IOWrapper, BaseIOMultiplexer


# Definitions #
# Classes #
class IOCallbackWrapper(BaseIOMultiplexer):
    # Class Attributes #
    default_get: ClassVar[str] = "normal_get"
    default_get_async: ClassVar[str] = "normal_get_async"
    default_put: ClassVar[str] = "normal_put"
    default_put_async: ClassVar[str] = "normal_put_async"
    default_join: ClassVar[str] = "join_callback_wrapped"
    default_join_async: ClassVar[str] = "join_callback_wrapped_async"

    # Attributes #
    wrapped: BaseIO | None = None

    callback: Callable | None = None
    callback_async: Callable | None = None

    callback_tasks: set[Task]

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        io_: BaseIO | None = None,
        callback: Callable | None = None,
        callback_async: Callable | None = None,
        get: str | None = None,
        get_async: str | None = None,
        put: str | None = None,
        put_async: str | None = None,
        join: str | None = None,
        join_async: str | None = None,
        *args: Any,
        init: bool = True,
        **kwargs: Any,
    ) -> None:
        # New Attributes #
        self.callback_tasks = set()

        # Parent Attributes #
        super().__init__(init=False)

        # Construction #
        if init:
            self.construct(
                io_,
                callback,
                callback_async,
                get,
                get_async,
                put,
                put_async,
                join,
                join_async,
                *args,
                **kwargs,
            )

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        io_: BaseIO | None = None,
        callback: Callable | None = None,
        callback_async: Callable | None = None,
        get: str | None = None,
        get_async: str | None = None,
        put: str | None = None,
        put_async: str | None = None,
        join: str | None = None,
        join_async: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        if io_ is not None:
            self.wrapped = io_

        if callback is not None:
            self.callback = callback

        if callback_async is not None:
            self.callback_async = callback_async

        if get is not None:
            self.get.select(get)

        if get_async is not None:
            self.get_async.select(get_async)

        if put is not None:
            self.put.select(put)

        if put_async is not None:
            self.put_async.select(put_async)

        if join is not None:
            self.join.select(join)

        if join_async is not None:
            self.join_async.select(join_async)

        super().construct(*args, **kwargs)

    # State
    def empty(self) -> bool:
        """Checks if the IO object is empty.

        Returns:
            True if the IO object is empty, False otherwise.
        """
        return self.wrapped.empty()

    def poll(self) -> bool:
        """Checks if the IO object has something in it.

        Returns:
            True if the IO object has something in it, False otherwise.
        """
        return self.wrapped.poll()

    # Callback Task Creation
    def create_callback_task(self) -> Task:
        task = create_task(self.callback_async())
        task.add_done_callback(self.callback_tasks.remove)
        self.callback_tasks.add(task)
        return task

    # Get
    def normal_get(self, *args: Any, **kwargs: Any) -> Any:
        return self.wrapped.get(*args, **kwargs)

    async def normal_get_async(self, *args: Any, **kwargs: Any) -> Any:
        return await self.wrapped.get_async(*args, **kwargs)

    def before_get(self, *args: Any, **kwargs: Any) -> Any:
        self.callback()
        return self.wrapped.get(*args, **kwargs)

    async def before_get_async(self, *args: Any, **kwargs: Any) -> Any:
        await self.create_callback_task()
        return await self.wrapped.get_async(*args, **kwargs)

    def after_get(self, *args: Any, **kwargs: Any) -> Any:
        result = self.wrapped.get(*args, **kwargs)
        self.callback()
        return result

    async def after_get_async(self, *args: Any, **kwargs: Any) -> Any:
        result = await self.wrapped.get_async(*args, **kwargs)
        await self.create_callback_task()
        return result

    # Put
    def normal_put(self, *args: Any, **kwargs: Any) -> None:
        self.wrapped.put(*args, **kwargs)

    async def normal_put_async(self, *args: Any, **kwargs: Any) -> None:
        await self.wrapped.put_async(*args, **kwargs)

    def before_put(self, *args: Any, **kwargs: Any) -> None:
        self.callback()
        self.wrapped.put(*args, **kwargs)

    async def before_put_async(self, *args: Any, **kwargs: Any) -> None:
        await self.create_callback_task()
        await self.wrapped.put_async(*args, **kwargs)

    def after_put(self, *args: Any, **kwargs: Any) -> None:
        self.wrapped.put(*args, **kwargs)
        self.callback()

    async def after_put_async(self, *args: Any, **kwargs: Any) -> None:
        await self.wrapped.put_async(*args, **kwargs)
        await self.create_callback_task()

    # Join
    def join_callback_wrapped(self, *args: Any, **kwargs: Any) -> None:
        """Joins using the joiner function or method.

        Args:
            *args: Positional arguments for joining.
            **kwargs: Keyword arguments for joining.
        """
        self.wrapped.join(*args, **kwargs)

    async def join_callback_wrapped_async(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously joins using the joiner_async function or method.

        Args:
            *args: Positional arguments for joining.
            **kwargs: Keyword arguments for joining.
        """
        await gather(*self.callback_tasks, self.wrapped.join_async(*args, **kwargs))
