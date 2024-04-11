""" delegatemethod.py.py

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
from typing import Any

# Third-Party Packages #
from baseobjects.typing import AnyCallable
from baseobjects.functions import BaseDecorator

# Local Packages #


# Definitions #
# Classes #
class delegatemethod(BaseDecorator):
    # Attributes #
    _wrapper_method: str = "delegate_call"
    proxy_method: str | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        method: AnyCallable | str | None = None,
        func: AnyCallable | None = None,
        *args: Any,
        wrapper_method: str | None = None,
        init: bool = True,
        **kwargs: Any,
    ) -> None:
        # Parent Attributes #
        super().__init__(*args, init=False, **kwargs)

        # Object Creation #
        if init:
            if isinstance(method, str):
                self.construct(method=method, func=func, wrapper_method=wrapper_method)
            else:
                self.construct(func=method, wrapper_method=wrapper_method)

    # Instance Methods #
    # Constructors
    def construct(
        self,
        method: AnyCallable | str | None = None,
        func: AnyCallable | None = None,
        *args: Any,
        wrapper_method: str | None = None,
        **kwargs: Any,
    ) -> None:
        """The constructor for this object.

        Args:
            func: The function to wrap.
            *args: Arguments for inheritance.
            wrapper_method: The name of the method which will act as the wrapper for this decorator.
            **kwargs: Keyword arguments for inheritance.
        """
        if method is not None:
            self.proxy_method = method

        super().construct(func=func, *args, wrapper_method=wrapper_method, **kwargs)

    # Calling
    def local_call(self, obj: "ProcessDelegate", *args: Any, **kwargs: Any) -> Any:
        """Delegates a function call of an object to the local execution.

        Args:
            obj: The object whose function call will be delegated.
            *args: The arguments of function call being delegated.
            **kwargs: The keyword arguments of function call being delegated.

        Returns:
            The result of the function call.
        """
        return self.__wrapped__(obj, *args, **kwargs)

    def delegate_call(self, obj: "ProcessDelegate", *args: Any, **kwargs: Any) -> Any:
        """Delegates a function call of an object to its corresponding remote server if it exists.

        Args:
            obj: The object whose function call will be delegated.
            *args: The arguments of function call being delegated.
            **kwargs: The keyword arguments of function call being delegated.

        Returns:
            The result of the function call.
        """
        if obj.is_proxy():
            if (proxy := obj._proxy) is not None and proxy._is_alive():
                return getattr(proxy, self.proxy_method or self.__name__)(*args, **kwargs)
            else:
                raise RuntimeError("Server process must be alive")
        else:
            return self.__wrapped__(obj, *args, **kwargs)
