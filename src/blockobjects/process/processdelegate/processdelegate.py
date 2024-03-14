""" processdelegate.py.py

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
from ..context import BaseProcessingContext, ContextualObject, ProxyInterface


# Definitions #
# Classes #
class ProcessDelegate(ContextualObject):
    """

    Class Attributes:

    Attributes:

    Args:

    """

    exposed: tuple = ()
    unexposed: tuple = ()

    # Attributes
    _is_remote: bool = False

    remote_process: ProxyInterface | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, *, context: BaseProcessingContext | None = None, init: bool = True) -> None:
        # New Attributes #


        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct(context=context)

    # Instance Methods #
    # Constructors/Destructors
    def construct(self, *, context: BaseProcessingContext | None = None) -> None:
        super().construct(context=context)

    # Context
    def set_context(self, context: BaseProcessingContext) -> None:
        super().set_context(context=context)

    # Remote
    def is_remote(self) -> bool:
        return self._is_remote

    def is_alive(self) -> bool:
        return False if self.remote_process is None else self.remote_process.is_alive()

    def create_remote_process(self, *args, **kwargs):
        self.remote_process = self.context.create_proxy(self, *args, **kwargs)
        self.remote_process.start()
        self.remote_process.execute_remote(name="set_remote", args=(False,))

