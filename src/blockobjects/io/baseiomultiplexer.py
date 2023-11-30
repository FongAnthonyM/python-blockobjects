""" baseiomultiplexer.py
An abstract class for IO Objects which use MethodMultiplexer for the get and put methods.
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
from typing import Any

# Third-Party Packages #
from baseobjects.functions import CallableMultiplexObject, MethodMultiplexer

# Local Packages #
from .baseio import BaseIO


# Definitions #
# Classes #
class BaseIOMultiplexer(BaseIO, CallableMultiplexObject):
    """An abstract class for IO Objects which use MethodMultiplexer for the get and put methods.

    Class Attributes:
        default_get: The default name of the method to use for getting.
        default_put: The default name of the method to use for putting.

    Attributes:
        get: The method multiplexer which manages which get method to run when called.
        put: The method multiplexer which manages which get method to run when called.

    Args:
        *args: Arguments for inheritance.
        **kwargs: Keyword arguments for inheritance.
    """
    default_get: str | None = None
    default_put: str | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # New Attributes #
        self.get: MethodMultiplexer = MethodMultiplexer(instance=self, select=self.default_get)
        self.put: MethodMultiplexer = MethodMultiplexer(instance=self, select=self.default_put)

        # Parent Attributes #
        super().__init__(*args, **kwargs)
