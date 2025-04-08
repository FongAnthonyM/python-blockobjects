#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" contexts_example.py
An example of how to use the processing contexts.
"""
# Imports #
# Standard Libraries #
from asyncio import run

# Third-Party Packages #
from blockobjects.io import IOContextualQueue
from blockobjects.process import DEFAULT_PROCESS_CONTEXT

# Local Packages #
from examples.blockgroup.exampleblockgroup import ExampleBlockGroup


# Definitions #
# Functions #
async def main():
    print("BlockGroup Example:")

    # Create Block Group
    group = ExampleBlockGroup(will_proxy=False)
    # Add Final Queue
    group.outputs.create_io("group_result", group="required", type_=IOContextualQueue)

    # Start Block Group
    print("Starting Block Group")
    await group.start_async()
    print("Block Group Started")

    # Wait for output
    first_output = await group.outputs.get_all_async()
    second_output = await group.outputs.get_all_async()

    # Stop Block Group
    print("Joining Block Group")
    await group.join_async()

    # Check Output
    print("Checking Output")
    print(f"First Output: {first_output['group_result'][1]} == False")


# Main #
if __name__ == "__main__":
    DEFAULT_PROCESS_CONTEXT.select_context("multiprocessing")
    run(main())
