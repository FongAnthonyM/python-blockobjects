""" proxyinterface.py.py

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
from abc import abstractmethod
from typing import Any

# Third-Party Packages #
from baseobjects import BaseObject

# Local Packages #


# Definitions #
# Classes #
class ProxyInterface(BaseObject):
    # Instance Methods #
    # State
    @abstractmethod
    def is_alive(self) -> bool:
        pass

    # Execution
    @abstractmethod
    async def execute_remote(self, name, args=(), kwargs={}) -> Any:
        pass
