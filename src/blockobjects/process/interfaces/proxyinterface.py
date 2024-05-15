""" proxyinterface.py
An interface which outlines the basis for a Proxy object.
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
from abc import abstractmethod

# Third-Party Packages #
from baseobjects import BaseObject

# Local Packages #


# Definitions #
# Classes #
class ProxyInterface(BaseObject):
    """An interface which outlines the basis for a Proxy object."""

    # Instance Methods #
    # State
    @abstractmethod
    def _is_alive(self) -> bool:
        """Returns True if the proxy server is alive, False otherwise."""

    # Server
    @abstractmethod
    def _kill_server(self) -> None:
        """Kills the server which the proxy is running on."""
