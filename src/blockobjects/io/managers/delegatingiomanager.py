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
from typing import ClassVar
from types import MethodType

# Third-Party Packages #
from src.blockobjects.process import ProcessDelegate

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
    local_methods: ClassVar[set] = {"set_callback_methods"}

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

    def set_callback_methods(self, method, method_async) -> None:
        if self.is_proxy():
            if (weak := getattr(method, "_self_", None)) is not None:
                method = MethodType(method.__wrapped__, weak())
            if (weak := getattr(method_async, "_self_", None)) is not None:
                method_async = MethodType(method_async.__wrapped__, weak())
            self._proxy.set_callback_methods(method, method_async)
        else:
            self.callback_method = method
            self.callback_method_async = method_async
