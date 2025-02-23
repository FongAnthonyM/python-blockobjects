""" rngblock.py
A Block which generates an array of random numbers.
"""
# Imports #
# Standard Libraries #
from typing import ClassVar, Any

# Third-Party Packages #
from blockobjects import BaseProducerBlock
import numpy as np

# Local Packages #


# Definitions #
# Classes #
class RNGBlock(BaseProducerBlock):
    """A Block which generates an array of random numbers.

    Attributes:
        inputs: The inputs manager of the Block.
        outputs: The outputs manager of the Block.
        execute: The method multiplexer which manages which execute method to run when called.
        input_names: The ordered tuple with the names of the inputs to an Block.
        _output_names: The ordered tuple with the names of the outputs to an Block.

        shape: The shape of the random array to generate.
        scale: The scale to apply to the random array.
        shift: The shift to apply to the random array.

    Args:
        shape: The shape of the random array to generate.
        scale: The scale to apply to the random array.
        shift: The shift to apply to the random array.
        *args: Arguments for inheritance.
        init_io: Determines if construct_io run during this construction.
        setup: Determines if setup will run during this construction.
        init: Determines if this object will construct.
        **kwargs: Keyword arguments for inheritance.
    """

    # Class Attributes #
    default_output_names: ClassVar[tuple[str, ...]] = ("out_array",)
    default_output_signal_names: ClassVar[tuple[str, ...]] = ("done_flag",)

    # Attributes #
    evaluation_limit: int = 0
    n_evaluations: int = 0

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        shape: tuple[int, ...] = (),
        scale: float = 1,
        shift: float = 0.0,
        evaluation_limit: int = 1,
        *args: Any,
        init: bool = True,
        **kwargs: Any,
    ) -> None:
        # New Attributes #
        self.shape: tuple[int, ...] = shape
        self.scale: float = scale
        self.shift: float = shift
        self.evaluation_limit = evaluation_limit

        # Parent Attributes #
        super().__init__(*args, init=False, **kwargs)

        # Construct #
        if init:
            self.construct(*args, **kwargs)

    # Evaluate
    def evaluate(self, *args, **kwargs: Any) -> Any:
        """Generates an array of random numbers.

        Args:
            *args: The arguments for evaluating.
            **kwargs: The keyword arguments for evaluating.

        Returns:
            A randomly generated array.
        """
        if self.n_evaluations >= self.evaluation_limit:
            self.stop_flag = True
            return self.no_output_sentinel
        else:
            print("rng")
            self.n_evaluations += 1
            return np.random.rand(*self.shape) * self.scale - self.shift

    # Teardown
    async def teardown(self) -> None:
        await self.outputs.put_item_async(self.signal_io_name, {"done_flag": True})
