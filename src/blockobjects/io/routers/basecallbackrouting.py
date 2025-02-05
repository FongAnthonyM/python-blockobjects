""" basecallbackrouting.py.py

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
from asyncio import create_task, Task
from collections.abc import Iterable, Iterator, Callable
from functools import partial
from typing import Any

# Third-Party Packages #
from baseobjects import BaseObject
from baseobjects.objects import CallbackManager

# Local Packages #


# Definitions #
# Functions #
async def _callback_put_async(__callback: Callable, __put: Callable, /, *args: Any, **kwargs: Any) -> None:
    await __put(await __callback(*args, **kwargs))


# Classes #
class BaseCallbackRouting(BaseObject):

    # Attributes #
    # Callbacks
    callback_manager: CallbackManager

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        *args: Any,
        init: bool = True,
        **kwargs: Any,
    ) -> None:
        # Attributes #
        self.callback_manager = CallbackManager(default_caller="call_while_condition_task_async")

        # Parent Attributes #
        super().__init__(init=False)

        # Construction #
        if init:
            self.construct(*args, **kwargs)

    # Instance Methods #
    # Callback Registration
    def register_conditional_callback(
        self,
        name: str,
        callback_kwargs: dict[str, Any] | None = None,
        condition_kwargs: dict[str, Any] | None = None,
        is_async: bool = False,
        **kwargs: Any,
    ) -> None:
        if is_async:
            call_method = self.create_async_callback_wrapper(**(callback_kwargs or {}))
            cond_method = self.create_async_condition_wrapper(**(condition_kwargs or {}))
        else:
            call_method = self.create_callback_wrapper(**(callback_kwargs or {}))
            cond_method = self.create_condition_wrapper(**(condition_kwargs or {}))
        self.callback_manager.register_conditional_callback(name, call_method, cond_method, is_async=is_async, **kwargs)

    async def register_conditional_callback_async(
        self,
        name: str,
        callback_kwargs: dict[str, Any] | None = None,
        condition_kwargs: dict[str, Any] | None = None,
        is_async: bool = False,
        **kwargs: Any,
    ) -> None:
        self.register_conditional_callback(name, callback_kwargs, condition_kwargs, is_async=is_async, **kwargs)

    def register_conditional_callbacks(
        self,
        callbacks: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
        callbacks_async: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
    ) -> None:
        if callbacks is not None:
            callback_iter = (
                (n, {"callback": self.create_callback_wrapper(**call), "condition": self.create_condition_wrapper(**cond)} | kw)
                for n, (call, cond, kw) in callbacks.items()
            )
        else:
            callback_iter = None

        if callbacks_async is not None:
            callback_async_iter = (
                (n, {"callback": self.create_callback_wrapper(**call),
                     "condition": self.create_condition_wrapper(**cond)} | kw)
                for n, (call, cond, kw) in callbacks.items()
            )
        else:
            callback_async_iter = None

        self.callback_manager.register_conditional_callbacks(callback_iter, callback_async_iter)

    async def register_conditional_callbacks_async(
        self,
        callbacks: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
        callbacks_async: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
    ) -> None:
        self.register_conditional_callbacks(callbacks, callbacks_async)

    def _register_inner_conditional_callbacks(
        self,
        names: Iterator[str],
        callbacks: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
        callbacks_async: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
    ) -> None:
        try:
            name = next(names)
        except StopIteration:
            self.register_conditional_callbacks(callbacks, callbacks_async)
        else:
            self.io_objects[name]._register_inner_conditional_callbacks(names, callbacks, callbacks_async)

    def register_inner_conditional_callbacks(
        self,
        names: Iterable[str] | str,
        callbacks: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
        callbacks_async: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
    ) -> None:
        if isinstance(names, str):
            self.io_objects[names].register_conditional_callbacks(callbacks=callbacks, callbacks_async=callbacks_async)
        else:
            self._register_inner_conditional_callbacks(iter(names), callbacks, callbacks_async)

    async def _register_inner_conditional_callbacks_async(
        self,
        names: Iterator[str],
        callbacks: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
        callbacks_async: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
    ) -> None:
        try:
            name = next(names)
        except StopIteration:
            await self.register_conditional_callbacks_async(callbacks, callbacks_async)
        else:
            await self.io_objects[name]._register_inner_conditional_callbacks_async(names, callbacks, callbacks_async)

    async def register_inner_conditional_callbacks_async(
        self,
        names: Iterable[str] | str,
        callbacks: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
        callbacks_async: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] | None = None,
    ) -> None:
        if isinstance(names, str):
            await self.io_objects[names].register_conditional_callbacks_async(callbacks, callbacks_async)
        else:
            await self._register_inner_conditional_callbacks_async(iter(names), callbacks, callbacks_async)

    # Callback Management
    def map_conditional_callbacks_to_scheduler(self, name: str, condition_names: Iterable[str]) -> None:
        self.callback_manager.map_conditionals_to_scheduler(name, condition_names)

    # Callback Creation
    def create_callback_wrapper(
        self,
        callback: Callable,
        get_method: str | Callable | None = None,
        put_method: str | Callable | None = None,
        *args: Any,
        callback_kwargs: dict[str, Any] | None = None,
        get_kwargs: dict[str, Any] | None = None,
        put_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Callable:
        # Resolve Get Method
        if get_method is not None:
            if isinstance(get_method, str):
                get_method = getattr(self, get_method)
            get_method_ = partial(get_method, **(get_kwargs or {}))
            has_get_method = True
        else:
            has_get_method = False

        # Resolve Put Method
        if put_method is not None:
            if isinstance(put_method, str):
                put_method = getattr(self, put_method)
            put_method_ = partial(put_method, **(put_kwargs or {}))
            has_put_method = True
        else:
            has_put_method = False

        # Resolve Callback Kwargs
        c_kwargs = callback_kwargs or {}

        # Create Callback Wrapper
        match has_get_method, has_put_method:
            case False, False:
                return partial(self.callback_wrapper, callback, **c_kwargs)
            case False, True:
                return partial(self.callback_get_wrapper, callback, get_method_, **c_kwargs)
            case True, False:
                return partial(self.callback_put_wrapper, callback, put_method_, **c_kwargs)
            case True, True:
                return partial(self.callback_get_put_wrapper, callback, get_method_, put_method_, **c_kwargs)

    def create_async_callback_wrapper(
        self,
        callback: Callable,
        get_method: str | Callable | None = None,
        put_method: str | Callable | None = None,
        *args: Any,
        callback_kwargs: dict[str, Any] | None = None,
        get_kwargs: dict[str, Any] | None = None,
        put_kwargs: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Callable:
        # Resolve Get Method
        if get_method is not None:
            if isinstance(get_method, str):
                get_method = getattr(self, get_method)
            get_method_ = partial(get_method, **(get_kwargs or {}))
            has_get_method = True
        else:
            has_get_method = False

        # Resolve Put Method
        if put_method is not None:
            if isinstance(put_method, str):
                put_method = getattr(self, put_method)
            put_method_ = partial(put_method, **(put_kwargs or {}))
            has_put_method = True
        else:
            has_put_method = False

        # Resolve Callback Kwargs
        c_kwargs = callback_kwargs or {}

        # Create Callback Wrapper
        match has_get_method, has_put_method:
            case False, False:
                return partial(self.callback_wrapper_async, callback, **c_kwargs)
            case False, True:
                return partial(self.callback_get_wrapper_async, callback, get_method_, **c_kwargs)
            case True, False:
                return partial(self.callback_put_wrapper_async, callback, put_method_, **c_kwargs)
            case True, True:
                return partial(self.callback_get_put_wrapper_async, callback, get_method_, put_method_, **c_kwargs)

    # Condition Creation
    def create_condition_wrapper(
        self,
        method: str | Callable = "poll_groups",
        *args: Any,
        **kwargs: Any,
    ) -> Callable:
        # Get condition wrapper method
        if isinstance(method, str):
            method = getattr(self, method)

        # Return callback wrapper
        return partial(self.condition_wrapper, method, *args, **kwargs)

    def create_async_condition_wrapper(
        self,
        method: str | Callable = "poll_groups_async",
        *args: Any,
        **kwargs: Any,
    ) -> Callable:
        # Build condition wrapper pieces
        if isinstance(method, str):
            method = getattr(self, method)

        # Return callback wrapper
        return partial(self.conditional_wrapper_async, method, *args, **kwargs)

    # Condition Methods and Functions
    @staticmethod
    def condition_wrapper(condition: Callable, *args: Any, **kwargs: Any) -> bool:
        return condition(*args, **kwargs)

    @staticmethod
    async def conditional_wrapper_async(condition: Callable, *args: Any, **kwargs: Any) -> bool:
        return await condition(*args, **kwargs)

    # Callback Methods and Functions
    @staticmethod
    def callback_wrapper(__callback: Callable, /, *args: Any, **kwargs: Any) -> None:
        __callback(*args, **kwargs)

    @staticmethod
    async def callback_wrapper_async(__callback: Callable, /, *args: Any, **kwargs: Any) -> Task:
        return create_task(__callback(*args, **kwargs))

    @staticmethod
    def callback_get_wrapper(__callback: Callable, __get: Callable, /, *args: Any, **kwargs: Any) -> None:
        __callback(__get(), *args, **kwargs)

    @staticmethod
    async def callback_get_wrapper_async(__callback: Callable, __get: Callable, /, *args: Any, **kwargs: Any) -> Task:
        return create_task(__callback(__get(), *args, **kwargs))

    @staticmethod
    def callback_put_wrapper(__callback: Callable, __put: Callable, /, *args: Any, **kwargs: Any) -> None:
        __put(__callback(*args, **kwargs))

    @staticmethod
    async def callback_put_wrapper_async(__callback: Callable, __put: Callable, /, *args: Any, **kwargs: Any) -> Task:
        return create_task(_callback_put_async(__callback, __put, *args, **kwargs))

    @staticmethod
    def callback_get_put_wrapper(
        __callback: Callable,
        __get: Callable,
        __put: Callable,
        /,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        __put(__callback(__get(), *args, **kwargs))

    @staticmethod
    async def callback_get_put_wrapper_async(
        __callback: Callable,
        __get: Callable,
        __put: Callable,
        /,
        *args: Any,
        **kwargs: Any,
    ) -> Task:
        return create_task(_callback_put_async(__callback, __put, __get(), *args, **kwargs))
