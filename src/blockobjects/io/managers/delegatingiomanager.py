""" delegatingiomanager.py
An IO object which maps named inputs to names outputs in a one-to-one manner.
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
import dill
from pickle import PicklingError
from typing import ClassVar
from types import MethodType
from weakref import ref

# Third-Party Packages #
from baseobjects import BaseMethod
from src.blockobjects.process import ProcessDelegate, delegatemethod

# Local Packages #
from .contextualiomanager import ContextualIOManager


# Definitions #
# Classes #
class DelegatingIOManager(ContextualIOManager, ProcessDelegate):
    """An IO object which maps named inputs to names outputs in a one-to-one manner.

    Class Attributes:
        default_get: The default name of the method to use for getting.
        default_put: The default name of the method to use for putting.

    Attributes:
        get: The method multiplexer which manages which get method to run when called.
        put: The method multiplexer which manages which get method to run when called.
        default_io: The default IO object type to populate this object when constructed.

    Args:
        io_: The input/outputs to be managed.
        *args: Arguments for inheritance.
        init: Determines if this object will construct.
        **kwargs: Keyword arguments for inheritance.
    """

    # Class Attributes #
    unexposed: ClassVar[set] = {"default_io"}
    local_methods: ClassVar[set] = {"update_server_io", "set_callbacks"}

    default_get: ClassVar[str] = "get_required"
    default_get_async: ClassVar[str] = "get_required_async"
    default_put: ClassVar[str] = "put_ordered"
    default_put_async: ClassVar[str] = "put_ordered_async"
    default_create_link: ClassVar[str] = "create_io_wrapper"

    # Attributes #
    # State
    will_proxy: bool = False

    # Linking
    def is_link_endpoint(self) -> bool:
        return not self.will_proxy

    def update_server_io(self):
        self._proxy.set_deepest_io(super().get_deepest_io())

    # Callback
    def set_callbacks(self, func, func_async) -> None:
        if isinstance(func, bytes):
            func = dill.loads(func)
        if isinstance(func_async, bytes):
            func_async = dill.loads(func_async)

        if self.is_proxy():
            if (weak := getattr(func, "_self_", None)) is not None:
                func = MethodType(func.__wrapped__, weak())
            if (weak := getattr(func_async, "_self_", None)) is not None:
                func_async = MethodType(func_async.__wrapped__, weak())

            try:
                self._proxy.set_callbacks(func, func_async)
            except:
                self._proxy.set_callbacks(dill.dumps(func), dill.dumps(func_async))
        else:
            self.callback = func
            self.callback_async = func_async
