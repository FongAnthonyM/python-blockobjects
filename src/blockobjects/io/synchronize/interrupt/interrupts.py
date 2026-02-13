"""interrupts.py
A container for several named interrupt.

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

# Third-Party Packages #
from baseobjects import BaseDict

# Local Packages #
from .interrupt import Interrupt


# Definitions #
# Classes #
class Interrupts(BaseDict):
    """A container for several named interrupt.

    Attributes:
        master_interrupt: An interrupt which is the parent for all contained interrupt.

    Args:
        dict_: A dictionary of interrupt to add to this container.
        *args: Arguments for inheritance.
        **kwargs: Keyword arguments for inheritance.
    """

    # Magic Methods #
    # Construction/Destruction
    def __init__(self, dict_: dict | None = None, /, *args, **kwargs) -> None:
        # New Attributes #
        self.master_interrupt: Interrupt = Interrupt()

        # Construction #
        super().__init__(dict_, *args, **kwargs)

    # Instance Methods #
    def set(self, name: str, interrupt: Interrupt | None) -> None:
        """Sets a contained interrupt.

        Args:
            name: The name of the interrupt to set.
            interrupt: The interrupt to set.
        """
        self.data[name] = interrupt

    def require(self, name: str, interrupt: Interrupt | None = None) -> Interrupt:
        """Adds an interrupt if it does not exist in the container.

        Args:
            name: The name of the interrupt to either get or create.
            interrupt: The interrupt to set if not in the container.

        Returns:
            The interrupt in the container or the newly created interrupt.
        """
        item = self.data.get(name, None)
        if item is None:
            self.data[name] = item = Interrupt(parent=self.master_interrupt) if interrupt is None else interrupt
        return item

    def remove(self, name: str) -> None:
        """Removes a contained interrupt.

        Args:
            name: The name of the interrupt to remove.
        """
        del self.data[name]

    def is_set(self, name: str) -> bool:
        """Checks if a contained interrupt is set.

        Args:
            name: The name of the interrupt to check.

        Returns:
            If the interrupt is set or not.
        """
        return self.get(name).is_set()

    def interrupt(self, name: str) -> None:
        """Sets the state of an interrupt to interrupted.

        Args:
            name: The name of the interrupt to set.
        """
        self.data[name].set()

    def interrupt_all(self) -> None:
        """Sets the state af all interrupt to interrupted."""
        for interrupt in self.data:
            interrupt.set()

    def interrupt_master(self) -> None:
        """Sets the state af the master interrupt to interrupted."""
        self.master_interrupt.set()

    def reset(self, name: str) -> None:
        """Resets the state of an interrupt to uninterrupted.

        Args:
            name: The name of the interrupt to clear.
        """
        self.data[name].clear()

    def reset_all(self) -> None:
        """Resets the state af all interrupt to uninterrupted."""
        for interrupt in self.data:
            interrupt.reset()

    def reset_master(self):
        """Resets the state af the master interrupt to uninterrupted."""
        self.master_interrupt.clear()
