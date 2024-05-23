#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" test_hdf5objects.py
Description:
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
from asyncio import run
from time import sleep

# Third-Party Packages #
from blockobjects.process import DEFAULT_PROCESS_CONTEXT

# Local Packages #
from examples.blocks.exampleblockgroup import ExampleBlockGroup


# Definitions #
# Functions #
async def main():
    # Create Block Group
    group = ExampleBlockGroup(will_proxy=True)
    # Start Block Group
    await group.start_async()

    # Wait for output
    first_output = await group.outputs.get_all_async()
    second_output = await group.outputs.get_all_async()
    third_output = await group.outputs.get_all_async()
    fourth_output = await group.outputs.get_all_async()

    # Stop Block Group
    await group.stop_async()

    # Check Output
    assert first_output


# Main #
if __name__ == "__main__":
    DEFAULT_PROCESS_CONTEXT.select_context("multiprocessing")
    run(main())
