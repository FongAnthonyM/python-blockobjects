"""isequalblock.py
A Block which checks if all values in the array are equal. Can select the equals methods.

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
from typing import ClassVar, Any

# Third-Party Packages #
from baseobjects.functions import MethodMultiplexer
from blockobjects import BaseBlock
import numpy as np

# Local Packages #


# Definitions #
# Classes #
class IsEqualBlock(BaseBlock):
    """A Block which checks if all values in the array are equal. Can select the equals methods.

    Attributes:
        inputs: The inputs manager of the Block.
        outputs: The outputs manager of the Block.
        execute: The method multiplexer which manages which execute method to run when called.
        input_names: The ordered tuple with the names of the inputs to a Block.
        _output_names: The ordered tuple with the names of the outputs to a Block.

        is_equal: The method multiplexer which manages which is_equal method to run when called.

    Args:
        equals_method: The name of the equals method to use.
        *args: Arguments for inheritance.
        init_io: Determines if construct_io run during this construction.
        setup: Determines if setup will run during this construction.
        init: Determines if this object will construct.
        **kwargs: Keyword arguments for inheritance.
    """

    # Class Attributes #
    default_input_names: ClassVar[tuple[str, ...]] = ("data",)
    default_output_names: ClassVar[tuple[str, ...]] = ("result",)
    default_equals_method: str = "all"
    default_input_signal_names: ClassVar[tuple[str, ...]] = ("stop_flag",)

    # Attributes #
    signal_callback_map = {"stop_callback": {"method": "stop_signal", "signals":("stop_flag",)}}

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        equals_method: str | None = None,
        *args: Any,
        init: bool = True,
        **kwargs: Any,
    ) -> None:
        # New Attributes #
        self.is_equal: MethodMultiplexer = MethodMultiplexer(instance=self, select=self.default_equals_method)

        # Parent Attributes #
        super().__init__(*args, init=False, **kwargs)

        # Construct #
        if init:
            self.construct(*args, equals_method=equals_method, **kwargs)

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        equals_method: str | None = None,
        *args: str | None,
        **kwargs: Any,
    ) -> None:
        """Constructs this object.

        Args:
            *args: Arguments for inheritance.
            **kwargs: Keyword arguments for inheritance.
        """
        if equals_method is not None:
            self.is_equal.select(equals_method)

        # Construct Parent #
        super().construct(*args, **kwargs)

    # Is Equal
    def all(self, data: np.ndarray) -> bool:
        """Checks if all the values in data are the same.

        Args:
            data: The array to check.

        Returns:
            The boolean if all values are the same.
        """
        return np.all(data)

    def unique(self, data: np.ndarray) -> bool:
        """Checks if all the values in data are unique.

        Args:
            data: The array to check.

        Returns:
            The boolean if all values are unique.
        """
        return np.unique(data).size == data.size

    # Evaluate
    def evaluate(self, data: np.ndarray, *args, **kwargs: Any) -> Any:
        """Checks if all values in the array are equal.

        Args:
            data: The array to check if all values are equal.
            *args: The arguments for evaluating.
            **kwargs: The keyword arguments for evaluating.

        Returns:
            The boolean if all values are equal.
        """
        print("IsEqualBlock.evaluate")
        return self.is_equal(data)

    # Teardown
    async def teardown(self) -> None:
        await self.outputs.put_item_async(self.signal_io_name, {"done_flag": True})
