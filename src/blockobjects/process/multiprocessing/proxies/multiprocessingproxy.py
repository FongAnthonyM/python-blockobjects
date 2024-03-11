""" multiprocessingproxy.py

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
from ...context import ProxyInterface
from .multiprocessingproxyserver import MultiprocessingProxyServer


# Definitions #
# Classes #
class MultiprocessingProxy(ProxyInterface):

    # Class Attributes #
    _proxy_name: str | None = None
    _server_type: type[MultiprocessingProxyServer] = MultiprocessingProxyServer

    # Class Methods #
    @classmethod
    def get_proxy_name(cls) -> str:
        return cls._proxy_name or cls.__name__

    @classmethod
    def set_server_type(cls, server_type: type[MultiprocessingProxyServer]) -> None:
        name = cls.get_proxy_name()
        if not hasattr(server_type, name):
            server_type.register(name, cls)
        cls._server_type = server_type

    # Attributes #
    proxy_server: MultiprocessingProxyServer


