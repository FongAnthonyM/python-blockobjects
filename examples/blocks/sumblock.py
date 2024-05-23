""" sumblock.py
A Block which scales the input ndarray and returns its sum, minium, and maximum.
"""
# Package Header #
from blockobjects.header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


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
    """A Block which scales the input ndarray and returns its sum, minium, and maximum."""

    # Class Attributes #
    default_input_names: ClassVar[tuple[str, ...]] = ("data", "scale")
    default_required_input: ClassVar[tuple[str, ...]] = ("data",)
    default_optional_input: ClassVar[dict[str, Any]] = {"scale": 1.0}
    default_output_names: ClassVar[tuple[str, ...]] = ("out_number", "scaled_min", "scaled_max")

    # Instance Methods #
    # Evaluate
    def evaluate(self, data: np.ndarray, scale: float = 1.0, *args, **kwargs: Any) -> Any:
        """Scales the given ndarray and returns some information from the array.

        Args:
            data: The ndarray to scale and return information on.
            scale: The amount to scale the data by.
            *args: The arguments for evaluating.
            **kwargs: The keyword arguments for evaluating.

        Returns:
            The sum, min, and max of the scaled array.
        """
        scaled_data = data * scale

        return scaled_data.sum(), scaled_data.min(), scaled_data.max()
