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
from .processdelegate import ProcessDelegate


# Definitions #
# Classes #
class delegatemethod(BaseDecorator):
    # Attributes #
    wrapper_method: str = "delegate_call"

    # Instance Methods #
    # Calling
    def delegate_call(self, obj: ProcessDelegate, *args: Any, **kwargs: Any) -> Any:
        """Delegates a function call of an object to its corresponding remote executor if it exists.

        Args:
            obj: The object whose function call will be delegated.
            *args: The arguments of function call being delegated.
            **kwargs: The keyword arguments of function call being delegated.

        Returns:
            The result of the function call.
        """
        if obj.is_remote:
            if (remote_process := obj.remote_process) is not None and remote_process.is_alive():
                return obj.remote_process.execute_remote(self.__name__, args, kwargs)
            else:
                raise RuntimeError("Remote process must be alive")
        else:
            return self._func_(obj, *args, **kwargs)
