""" functionreducer.py
Reduces a callable serialized object containing the build function and its arguments.
"""
# Package Header #
from ....header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Standard Libraries #
from collections.abc import Callable
from multiprocessing.reduction import ForkingPickler
from functools import partial
from types import FunctionType
from typing import Any

# Third-Party Packages #
import dill

# Local Packages #


# Definitions #
# function #
def reducefunction(function: Callable) -> tuple[Callable, tuple[Any, ...]]:
    """Reduces a callable serialized object containing the build function and its arguments.

    Args:
        function: The callable object to be reduced.

    Returns:
        A tuple with the build function and the arguments for the build function.
    """
    return rebuildfunction, (dill.dumps(function),)


def rebuildfunction(dill_function: bytes) -> Callable:
    """Rebuilds a callable serialized object containing the build function and its arguments.

    Args:
        dill_function: The serialized callable object to be rebuilt.

    Returns:
        The rebuilt callable object.
    """
    return dill.loads(dill_function)


def reducer_override(self, obj: Any) -> tuple[type, tuple[Any, ...]] | type[NotImplemented]:
    if isinstance(obj, FunctionType) and obj.__name__ != "<lambda>":
        return reducefunction(obj)
    else:
        return NotImplemented


def reducer_override_override(
    self,
    obj: Any,
    parent_method: Callable,
) -> tuple[type, tuple[Any, ...]] | type[NotImplemented]:
    if not isinstance(obj, FunctionType) or obj in self.dispatch_table:
        return parent_method(self, obj)
    else:
        return reducefunction(obj)


# Registration #
if (method := getattr(ForkingPickler, "reducer_override", None)) is None:
    ForkingPickler.reducer_override = reducer_override
else:
    ForkingPickler.reducer_override = partial(reducer_override_override, parent_method=method)
