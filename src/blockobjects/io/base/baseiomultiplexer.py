""" baseiomultiplexer.py
BaseIOMultiplexer sets the get and put methods to be MethodMultiplexer objects which dispatches the get and put
methods from collection of methods based on the selected method name. By default, the MethodMultiplexer uses its
corresponding BaseIOMultiplexer instance as the source of the methods to dispatch.

In the context of IO Objects, this means any BaseIOMultiplexer subclass will have get and put methods which can be
changed to any method during runtime. This allows the subclasses to change how they route IO dynamically, either
during construction or runtime.
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
from typing import ClassVar, Any

# Third-Party Packages #
from baseobjects.functions import MethodMultiplexer

# Local Packages #
from .baseio import BaseIO


# Definitions #
# Classes #
class BaseIOMultiplexer(BaseIO):
    """An abstract class for IO Objects which use MethodMultiplexer objects for the get and put methods.

    BaseIOMultiplexer sets the get and put methods to be MethodMultiplexer objects which dispatches the get and put
    methods from collection of methods based on the selected method name. By default, the MethodMultiplexer uses its
    corresponding BaseIOMultiplexer instance as the source of the methods to dispatch.

    In the context of IO Objects, this means any BaseIOMultiplexer subclass will have get and put methods which can be
    changed to any method during runtime. This allows the subclasses to change how they route IO dynamically, either
    during construction or runtime.

    Class Attributes:
        default_get: The default name of the method to use for getting.
        default_get_async: The default name of the method to use for asynchronously getting.
        default_put: The default name of the method to use for putting.
        default_put_async: The default name of the method to use for asynchronously putting.
        default_join: The default name of the method to use for joining.
        default_join_async: The default name of the method to use for asynchronously joining.

    Attributes:
        get: The method multiplexer which manages which get method to run when called.
        get_async: The method multiplexer which manages which asynchronous get method to run when called.
        put: The method multiplexer which manages which put method to run when called.
        put_async: The method multiplexer which manages which asynchronous put method to run when called.
        join: The method multiplexer which manages which join method to run when called.
        join_async: The method multiplexer which manages which asynchronous join method to run when called.

    Args:
        *args: Arguments for inheritance.
        **kwargs: Keyword arguments for inheritance.
    """

    # Class Attributes #
    default_get: ClassVar[str | None] = None
    default_get_async: ClassVar[str | None] = None
    default_put: ClassVar[str | None] = None
    default_put_async: ClassVar[str | None] = None
    default_join: ClassVar[str | None] = None
    default_join_async: ClassVar[str | None] = None

    # Attributes #
    get: MethodMultiplexer
    get_async: MethodMultiplexer
    put: MethodMultiplexer
    put_async: MethodMultiplexer
    join: MethodMultiplexer
    join_async: MethodMultiplexer

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        # New Attributes #
        self.get = MethodMultiplexer(instance=self, select=self.default_get)
        self.get_async = MethodMultiplexer(instance=self, select=self.default_get_async)
        self.put = MethodMultiplexer(instance=self, select=self.default_put)
        self.put_async = MethodMultiplexer(instance=self, select=self.default_put_async)
        self.join = MethodMultiplexer(instance=self, select=self.default_join)
        self.join_async = MethodMultiplexer(instance=self, select=self.default_join_async)

        # Parent Attributes #
        super().__init__(*args, **kwargs)
