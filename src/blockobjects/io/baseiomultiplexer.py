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
from typing import ClassVar, Any

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
        default_get_async: The default name of the method to use for asynchronously getting.
        default_put_async: The default name of the method to use for asynchronously putting.
        default_put: The default name of the method to use for putting.

    Attributes:
        get: The method multiplexer which manages which get method to run when called.
        get_async: The method multiplexer which manages which asynchronous get method to run when called.
        put_async: The method multiplexer which manages which asynchronous putt method to run when called.
        put: The method multiplexer which manages which put method to run when called.

    Args:
        *args: Arguments for inheritance.
        **kwargs: Keyword arguments for inheritance.
    """
    # Class Attributes #
    default_get: ClassVar[str | None] = None
    default_get_async: ClassVar[str | None] = None
    default_put: ClassVar[str | None] = None
    default_put_async: ClassVar[str | None] = None

    # Attributes #
    get: MethodMultiplexer
    get_async: MethodMultiplexer
    put: MethodMultiplexer
    put_async: MethodMultiplexer

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # New Attributes #
        self.get = MethodMultiplexer(instance=self, select=self.default_get)
        self.get_async = MethodMultiplexer(instance=self, select=self.default_get_async)
        self.put = MethodMultiplexer(instance=self, select=self.default_put)
        self.put_async = MethodMultiplexer(instance=self, select=self.default_put_async)

        # Parent Attributes #
        super().__init__(*args, **kwargs)
