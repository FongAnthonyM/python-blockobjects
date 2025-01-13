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
from types import FunctionType
from typing import Any

# Third-Party Packages #
import dill

# Local Packages #


# Definitions #
# Classes #
def reducefunction(function: Callable) -> tuple[type, tuple[Any, ...]]:
    """Reduces a callable serialized object containing the build function and its arguments.

    Args:
        function: The callable object to be reduced.

    Returns:
        A tuple with the build function and the arguments for the build function.
    """
    return dill.loads, (dill.dumps(function),)


# Registration #
ForkingPickler.register(FunctionType, reducefunction)
