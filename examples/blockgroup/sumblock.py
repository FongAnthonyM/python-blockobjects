""" sumblock.py
A Block which scales the input ndarray and returns its sum, minium, and maximum.
"""
# Imports #
# Standard Libraries #
from typing import ClassVar, Any

# Third-Party Packages #
import numpy as np
from blockobjects import BaseBlock

# Local Packages #


# Definitions #
# Classes #
class SumBlock(BaseBlock):
    """A Block which scales the input ndarray and returns its sum, minimum, and maximum."""

    # Class Attributes #
    default_input_names: ClassVar[tuple[str, ...]] = ("data", "scale")
    default_required_input: ClassVar[tuple[str, ...]] = ("data",)
    default_optional_input: ClassVar[dict[str, Any]] = {"scale": 1.0}
    default_output_names: ClassVar[tuple[str, ...]] = ("out_number", "scaled_min", "scaled_max")
    default_input_signal_names: ClassVar[tuple[str, ...]] = ("stop_flag",)
    default_output_signal_names: ClassVar[tuple[str, ...]] = ("done_flag",)

    # Attributes #
    signal_callback_map = {"stop_callback": {"method": "stop_signal", "signals":("stop_flag",)}}

    # Instance Methods #
    # Evaluate
    def evaluate(self, data: np.ndarray, scale: float = 1.0, *args: Any, **kwargs: Any) -> Any:
        """Scales the given ndarray and returns some information from the array.

        Args:
            data: The ndarray to scale and return information on.
            scale: The amount to scale the data by.
            *args: The arguments for evaluating.
            **kwargs: The keyword arguments for evaluating.

        Returns:
            The sum, min, and max of the scaled array.
        """
        print("sum")
        scaled_data = data * scale

        return scaled_data.sum(), scaled_data.min(), scaled_data.max()

    # Teardown
    async def teardown(self) -> None:
        await self.outputs.put_item_async(self.signal_io_name, {"done_flag": True})
