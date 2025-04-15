""" functionreducer.py
Reduces a callable serialized object containing the build function and its arguments.
"""
# Header #
__package_name__ = "blockobjects"

__author__ = "Anthony Fong"
__credits__ = ["Anthony Fong"]
__copyright__ = "Copyright 2022, Anthony Fong"
__license__ = "MIT"

__version__ = "0.1.0"


# Imports #
# Standard Libraries #
from collections.abc import Callable
from inspect import CO_NESTED
from multiprocessing.reduction import ForkingPickler
from functools import partial
from types import FunctionType
from typing import Any

# Third-Party Packages #
import dill

# Local Packages #


# Definitions #
# Functions #
def reducefunction(function: Callable) -> tuple[Callable, tuple[Any, ...]]:
    """Reduces a callable serialized object containing the build function and its arguments.

    Args:
        function: The callable object to be reduced.

    Returns:
        A tuple with the build function and the arguments for the build function.
    """
    return dill.loads, (dill.dumps(function),)


def _dill_reduce(self, obj: Any) -> bool:
    """Determines if the given object should be reduced by dill.

    This function checks if the provided object is both a function and either a lambda function or a nested
    function, based on its characteristics such as its name and code flags.

    Args:
        self: The instance of the class that contains this method.
        obj: object. The object to be checked for being a lambda or nested function.

    Returns:
        bool: True if the given object should be reduced by dill.
    """
    return isinstance(obj, FunctionType) and (obj.__name__ == "<lambda>" or obj.__code__.co_flags & CO_NESTED)


def reducer_override(self, obj: Any) -> tuple[type, tuple[Any, ...]] | type[NotImplemented]:
    """A function which will override the reducer method of a Pickler.

    This method provides an alternative implementation for the reduction logic of a Pickler. It determines whether the
    object should be handled using a custom reduction function or defaults to the standard behavior.

    Args:
        self: The current instance of the class invoking this method.
        obj: The object to be analyzed and potentially reduced.

    Returns:
        tuple[type, tuple[Any, ...]]: The custom reduced representation of the object when successfully handled.
        type[NotImplemented]: A marker indicating that the reduction should follow the standard dispatcher.
    """
    return reducefunction(obj) if _dill_reduce(self, obj) else NotImplemented


def reducer_override_override(
    self,
    obj: Any,
    parent_method: Callable,
) -> tuple[type, tuple[Any, ...]] | type[NotImplemented]:
    """A function which will override the reducer method of a Pickler, further overriding a parent method.

    This method provides an alternative implementation for the reduction logic of a Pickler. It determines whether the
    object should be handled using a custom reduction function or defaults to the standard behavior.

    Args:
        self: The current instance of the class invoking this method.
        obj: The object to be analyzed and potentially reduced.
        parent_method: The parent or supper method to run if the condition is not met.

    Returns:
        tuple[type, tuple[Any, ...]]: The custom reduced representation of the object when successfully handled.
        type[NotImplemented]: A marker indicating that the reduction should follow the standard dispatcher.
    """
    return reducefunction(obj) if _dill_reduce(self, obj) else parent_method(self, obj)


# Registration #
# Override the ForkingPickler's reduce method to allow function reduction
if (method := getattr(ForkingPickler, "reducer_override", None)) is None:
    # Simple function override if there was no reducer_override
    ForkingPickler.reducer_override = reducer_override
else:
    # Use override_override if there was a reducer_override present
    ForkingPickler.reducer_override = partial(reducer_override_override, parent_method=method)
