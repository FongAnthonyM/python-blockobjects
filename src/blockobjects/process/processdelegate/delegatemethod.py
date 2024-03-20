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
from baseobjects.functions import BaseDecorator

# Local Packages #


# Definitions #
# Classes #
class delegatemethod(BaseDecorator):
    # Attributes #
    _wrapper_method: str = "delegate_call"

    # Instance Methods #
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
        return self._func_(obj, *args, **kwargs)

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
                return getattr(proxy, self.__name__)(*args, **kwargs)
            else:
                raise RuntimeError("Server process must be alive")
        else:
            return self._func_(obj, *args, **kwargs)
