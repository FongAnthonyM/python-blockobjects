""" arbitratingiomanager.py
An IO object which maps named inputs to names outputs in a one-to-one manner.
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
from typing import ClassVar, Any

# Third-Party Packages #
import dill
from baseobjects import BaseMethod
from ...process import ProcessArbitrator, arbitratemethod

# Local Packages #
from .contextualiomanager import ContextualIOManager


# Definitions #
# Classes #
class ArbitratingIOManager(ContextualIOManager, ProcessArbitrator):
    """An IO object which maps named inputs to names outputs in a one-to-one manner.

    Class Attributes:
        default_get: The default name of the method to use for getting.
        default_put: The default name of the method to use for putting.

    Attributes:
        get: The method multiplexer which manages which get method to run when called.
        put: The method multiplexer which manages which get method to run when called.
        default_io: The default IO object type to populate this object when constructed.

    Args:
        io_: The input/outputs to be managed.
        *args: Arguments for inheritance.
        init: Determines if this object will construct.
        **kwargs: Keyword arguments for inheritance.
    """

    # Class Attributes #
    _memory_deletables: tuple = ("links_to", "links_from", "endpoints")
    unexposed: ClassVar[set] = {
        "is_endpoint_link",
        "is_listen_link",
        "default_io",
    }
    local_methods: ClassVar[set] = {
        "create_io_wrapper",
        "link_forward",
        "link_backward",
        "update_server_io",
        "update_server_io_async",
    }

    default_get: ClassVar[str] = "get_required"
    default_get_async: ClassVar[str] = "get_required_async"
    default_put: ClassVar[str] = "put_ordered"
    default_put_async: ClassVar[str] = "put_ordered_async"
    default_create_link: ClassVar[str] = "create_io_wrapper"

    # Attributes #
    # State
    will_proxy: bool = False

    # Pickling
    def __getstate__(self) -> dict[str, Any]:
        """Creates a dictionary of attributes which can be used to rebuild this object.

        Returns:
            A dictionary of this object's attributes.
        """
        state = super().__getstate__()
        # Save memory by deleting large unused attributes.
        if self.is_alive():
            for name in self._memory_deletables:
                if name in state:
                    del state[name]

        return state

    # Linking
    def is_remote(self) -> bool:
        return self.is_alive() or self.will_proxy

    def update_server_io(self):
        self._proxy.set_deepest(super().get_deepest())

    async def update_server_io_async(self):
        await self._proxy.set_deepest_async(super().get_deepest())

    # Proxy
    def _stop_server(self, update: bool = True, exclude: set | None = None) -> None:
        """Stops the remote server relative to this object.

        Args:
            update: Determines if this object should be updated from the server before stopping.
        """
        self.stop()
        super()._stop_server(update, exclude)
