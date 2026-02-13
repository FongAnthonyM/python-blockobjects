"""baseiomanager.py
An IO object which maps named inputs to names outputs in a one-to-one manner.

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

# Third-Party Packages #

# Local Packages #
from ..routers import IORouter


# Definitions #
# Classes #
class BaseIOManager(IORouter):
    """An abstract base class for an IO Manager which is an IORouter with more IO manipulation."""
