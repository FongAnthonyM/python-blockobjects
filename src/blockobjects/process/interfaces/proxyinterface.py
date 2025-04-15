""" proxyinterface.py
An interface which outlines the basis for a Proxy object.
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
