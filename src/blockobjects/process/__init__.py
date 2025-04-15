""" __init__.py

"""
# Header #
__package_name__ = "blockobjects"

__author__ = "Anthony Fong"
__credits__ = ["Anthony Fong"]
__copyright__ = "Copyright 2022, Anthony Fong"
__license__ = "MIT"

__version__ = "0.1.0"


# Imports #
# Local Packages #
from .interfaces import *
from .context import *
from .processarbitrator import *


# Defaults #
ProcessArbitrator._proxy_context = DEFAULT_PROCESS_CONTEXT
