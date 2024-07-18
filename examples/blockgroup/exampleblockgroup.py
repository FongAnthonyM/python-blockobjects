""" exampleblockgroup.py
A Block which generates a random array then finds the sum of the array twice and compares the outputs
"""
# Imports #
# Standard Libraries #
from typing import ClassVar, Any

# Third-Party Packages #
from blockobjects import BlockGroup
from blockobjects.io import IORouter

# Local Packages #
from .rngblock import RNGBlock
from .sumblock import SumBlock
from .isequalblock import IsEqualBlock


# Definitions #
# Classes #
class ExampleBlockGroup(BlockGroup):
    """A Block which generates a random array then finds the sum of the array twice and compares the outputs."""
    default_output_names: ClassVar[tuple[str, ...]] = ("group_result",)

    # Instance Methods #
    # Blocks
    def create_blocks(
        self,
        shape: tuple[int, ...] = (100, 100),
        *args: Any,
        override: bool = False,
        **kwargs: Any,
    ) -> None:
        """Creates the inner blockgroup.

        Args:
            *args: The arguments for creating the inner blockgroup.
            override: Determines if the inner blockgroup will be overridden.
            **kwargs: The keyword arguments for creating the inner blockgroup.
        """
        # Create Blocks
        self.blocks["generator"] = RNGBlock(shape=shape)
        self.blocks["sum_1"] = SumBlock()
        self.blocks["sum_2"] = SumBlock()
        self.blocks["checker"] = IsEqualBlock(equals_method="unique")

    # IO
    def link_inner_io(self, *args: Any, **kwargs: Any) -> None:
        """Links the inner blockgroup' IO.

        Args:
            *args: The arguments for creating linking the inner blockgroup' IO.
            **kwargs: The keyword arguments for creating linking the inner blockgroup' IO.
        """
        # Get Blocks
        generator = self.blocks["generator"]
        sum_1 = self.blocks["sum_1"]
        sum_2 = self.blocks["sum_2"]
        checker = self.blocks["checker"]

        # Group Inputs
        # No inputs to group because it generates its own data.

        # Inner Block IO
        # Route the RNG output to inputs of both the sum block.
        generator_router = IORouter(names=("sum_1", "sum_2"))  # Create a router to route the output to multiple inputs.
        generator.outputs.link_forward("out_array", generator_router)  # Link the output to the router.
        generator_router.link_forward("sum_1", sum_1.inputs, "data")  # Link the router to the sum block.
        generator_router.link_forward("sum_2", sum_2.inputs, "data")  # Link the router to the sum block.

        # Aggregate the sum outputs to a single IO and send to the checker.
        sum_1.outputs.link_forward("out_number", checker.inputs, "data")
        sum_2.outputs.link_forward("out_number", checker.inputs, "data")

        # Group Outputs
        checker.outputs.link_forward("result", self.outputs, "group_result")  # Can link the IO of single IO items.

