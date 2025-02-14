""" routefunctions.py.py

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

# Local Packages #


# Definitions #
# Functions #
# These Functions are routing functions which facilitate how IO is routed during callback
def bool_and(inputs: dict[str, Any]) -> Any:
    return all(inputs.values())


async def bool_and_async(inputs: dict[str, Any]) -> Any:
    return all(inputs.values())
