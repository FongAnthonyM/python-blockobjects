""" __init__.py

"""
# Package Header #
from ..header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Local Packages #
from .context import *
from .asynccontext import *
from .multiprocessing import *
from .processdelegate import *


# Defaults #
DEFAULT_PROCESS_CONTEXT = ManagerContext()
BaseContextualObject._context = DEFAULT_PROCESS_CONTEXT
