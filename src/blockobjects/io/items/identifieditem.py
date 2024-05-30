""" identifieditem.py
A class which represents an item with its associated identifiers.
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
from typing import Any, NamedTuple

# Third-Party Packages #

# Local Packages #


# Definitions #
# Classes #
class IdentifiedItem(NamedTuple):
    """A class which represents an item with its associated identifiers."""
    ids: tuple[bytes, ...]
    item: Any
