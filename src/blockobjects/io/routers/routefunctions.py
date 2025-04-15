""" routefunctions.py.py

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
