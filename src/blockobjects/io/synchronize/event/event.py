""" event.py

"""
# Package Header #
from ....header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Standard Libraries #

# Third-Party Packages #

# Local Packages #
from ....process.context import BaseProcessContext, DEFAULT_PROCESS_CONTEXT
from ....process.context.synchronize import ContextualEvent


# Definitions #
# Classes #
class Event(ContextualEvent):
    """"""
    default_context: BaseProcessContext = DEFAULT_PROCESS_CONTEXT

