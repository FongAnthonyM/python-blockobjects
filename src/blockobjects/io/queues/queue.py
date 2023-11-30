""" queue.py

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
from ...process.context import BaseProcessContext, DEFAULT_PROCESS_CONTEXT
from ...process.context import ContextualQueue


# Definitions #
# Classes #
class Queue(ContextualQueue):
    """"""
    default_context: BaseProcessContext = DEFAULT_PROCESS_CONTEXT

