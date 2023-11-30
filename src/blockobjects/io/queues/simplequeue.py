""" simplequeue.py

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
from ...process.context import ContextualSimpleQueue


# Definitions #
# Classes #
class SimpleQueue(ContextualSimpleQueue):
    """"""
    default_context: BaseProcessContext = DEFAULT_PROCESS_CONTEXT

