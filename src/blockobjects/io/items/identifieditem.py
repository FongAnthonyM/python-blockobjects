"""identifieditem.py
A class which represents an item with its associated identifiers.

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
from typing import Any, NamedTuple

# Third-Party Packages #

# Local Packages #


# Definitions #
# Classes #
class IdentifiedItem(NamedTuple):
    """A class which represents an item with its associated identifiers."""
    ids: tuple[bytes, ...]
    item: Any
