""" arbitratingiomanager.py
An IO object which maps named inputs to names outputs in a one-to-one manner.
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

# Third-Party Packages #

# Local Packages #
from ..routers import IORouter


# Definitions #
# Classes #
class BaseIOManager(IORouter):
    """An abstract base class for an IO Manager which is an IORouter with more IO manipulation."""
