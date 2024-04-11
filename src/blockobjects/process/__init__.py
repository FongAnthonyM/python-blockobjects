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
DEFAULT_PROCESS_CONTEXT.select_context("async")
BaseContextualObject._context = DEFAULT_PROCESS_CONTEXT
ProcessDelegate._proxy_context = DEFAULT_PROCESS_CONTEXT
