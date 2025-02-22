#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" example.py
An example of how to create and use a Block.
"""
# Imports #
# Standard Libraries #
import asyncio
from os import getpid
from typing import Any

# Third-Party Packages #
from blockobjects import BaseBlock
from blockobjects.io import IOContextualQueue
from blockobjects.process import DEFAULT_PROCESS_CONTEXT


# Definitions #
# Classes #
class ExampleBlock(BaseBlock):
    # Class Attributes #
    default_input_names = ("first", "second", "third", "fourth")
    default_required_input = ("first", "third")
    default_optional_input = {"second": 2, "fourth": 4}
    default_output_names = ("out_one", "out_two")

    # Attributes #
    # New attributes to be used in the tests
    setup_flag: bool = False
    teardown_flag: bool = False

    # Setup
    def setup(self, *args: Any, **kwargs: Any) -> None:
        """A method for setting up the object."""
        self.setup_flag = True
        print(f"PID {getpid()}: setup_flag")

    # Evaluate
    def evaluate(self, first=1, second=0, third=1, fourth=0, *args, **kwargs) -> Any:
        """A method for evaluating the object."""
        out_one = first * second
        out_two = third * fourth
        print(f"PID {getpid()}: evaluate_flag")
        return out_one, out_two

    # Teardown
    def teardown(self, *args: Any, **kwargs: Any) -> None:
        """A method for tearing down the object."""
        self.teardown_flag = True
        print(f"PID {getpid()}: teardown_flag")


# Functions #
async def asyncio_example():
    # Print some information
    print("Asyncio Example:")
    print(f"The main PID is {getpid()} \n")

    # Set the processing context (not necessary if running locally)
    DEFAULT_PROCESS_CONTEXT.select_context("multiprocessing")

    # Create Block
    block = ExampleBlock(init_setup=False)
    # Add Final Queues to store information
    block.outputs.create_io("out_one", group="required", type_=IOContextualQueue)
    block.outputs.create_io("out_two", group="required", type_=IOContextualQueue)

    # Start Block
    print("Start Block")
    print(f"PID {getpid()}: start called")
    await block.start_async()

    # Put Inputs
    print(f"\nPID {getpid()}: putting inputs")
    await block.inputs.put_item_async("first", 2)
    await block.inputs.put_item_async("third", 3)

    # Get Outputs
    print(f"\nPID {getpid()}: getting outputs")
    outputs = await block.outputs.get_all_async()

    # Stop Block
    print(f"\nPID {getpid()}: stop called")
    await block.stop_async()

    print("\nResults:")
    print(f"setup_flag: {block.setup_flag} == True")
    print(f"teardown_flag: {block.teardown_flag} == True")
    print(f"out_one: {outputs['out_one'][1]} == 4")
    print(f"out_two: {outputs['out_two'][1]} == 12")
    print("")


async def multiprocessing_example_async():
    # Print some information
    print("Multiprocessing Example:")
    print(f"The main PID is {getpid()} \n")

    # Set the processing context
    DEFAULT_PROCESS_CONTEXT.select_context("multiprocessing")

    # Create Block
    block = ExampleBlock(will_proxy=True, init_setup=False)
    # Add Final Queues to store information
    block.outputs.create_io("out_one", group="required", type_=IOContextualQueue)
    block.outputs.create_io("out_two", group="required", type_=IOContextualQueue)

    # Start Block
    print("Start Block")
    print(f"PID {getpid()}: start called")
    await block.start_async()

    # Put Inputs
    print(f"\nPID {getpid()}: putting inputs")
    await block.inputs.put_item_async("first", 2)
    await block.inputs.put_item_async("third", 3)

    # Get Outputs
    print(f"\nPID {getpid()}: getting outputs")
    outputs = await block.outputs.get_all_async()

    # Stop Block
    print(f"\nPID {getpid()}: stop called")
    await block.stop_async()

    print("\nResults:")
    print(f"setup_flag: {block.setup_flag} == True")
    print(f"teardown_flag: {block.teardown_flag} == True")
    print(f"out_one: {outputs['out_one'][1]} == 4")
    print(f"out_two: {outputs['out_two'][1]} == 12")
    print("")

# Main #
if __name__ == "__main__":
    asyncio.run(asyncio_example())
    asyncio.run(multiprocessing_example_async())
