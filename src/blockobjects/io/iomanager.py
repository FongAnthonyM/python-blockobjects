""" iomanager.py
An IO object which maps named inputs to names outputs in a one-to-one manner.
"""
# Package Header #
from ..header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Standard Libraries #
from asyncio import gather
from collections.abc import Iterable
from typing import ClassVar, Any

# Third-Party Packages #
from ..process import ProcessDelegate

# Local Packages #
from .iorouter import IORouter


# Definitions #
# Classes #
class IOManager(IORouter, ProcessDelegate):
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

    default_get: ClassVar[str] = "get_required"
    default_get_async: ClassVar[str] = "get_required_async"
    default_put: ClassVar[str] = "put_ordered"
    default_put_async: ClassVar[str] = "put_ordered_async"
