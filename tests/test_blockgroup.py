#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" test_blockgroup.py
Test for the baseobjects package.
"""
from typing import Any

# Package Header #
from src.blockobjects.header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Standard Libraries #
from asyncio import sleep, run
import pickle
from os import getpid

# Third-Party Packages #
import pytest
import ray

# Local Packages #
from src.blockobjects.process import DEFAULT_PROCESS_CONTEXT
from src.blockobjects.process.context import ManagerContext
from src.blockobjects.process.multiprocessing import MultiProcessingContext
from src.blockobjects.process.processdelegate import ProcessDelegate
from src.blockobjects.blocks import BaseBlock, BlockGroup
from tests.test_bases import ClassTest
from src.rayblocks import RayContext


# Definitions #
DEFAULT_PROCESS_CONTEXT.select_context("ray")


# Classes #
class ExampleOne(BaseBlock):
    # Class Attributes #
    default_input_names = ("first", "second", "third", "fourth")
    default_required_input = ("first", "third")
    default_optional_input = {"second": 2, "fourth": 4}
    default_output_names = ("out_one", "out_two")

    # Attributes #
    setup_flag: bool = False
    teardown_flag: bool = False

    # Setup
    def setup(self, *args: Any, **kwargs: Any) -> None:
        """A method for setting up the object."""
        self.setup_flag = True
        # print("setup_flag")

    # Evaluate
    def evaluate(self, first=1, second=0, third=1, fourth=0) -> Any:
        out_one = first * second
        out_two = third * fourth
        print("evaluate_flag")
        return out_one, out_two

    # Teardown
    def teardown(self, *args: Any, **kwargs: Any) -> None:
        """A method for setting up the object."""
        self.teardown_flag = True
        # print("teardown_flag")


class GroupOne(BlockGroup):
    # Class Attributes #
    default_input_names = ("one", "two")
    default_required_input = ("one", "two")
    # default_optional_input = {"second": 2, "fourth": 4}
    default_output_names = ("out_one", "out_two")

    # Blocks
    def create_blocks(self, *args: Any, override: bool = False, **kwargs: Any) -> None:
        """Creates the inner blocks.

        Args:
            *args: The arguments for creating the inner blocks.
            override: Determines if the inner blocks will be overridden.
            **kwargs: The keyword arguments for creating the inner blocks.
        """
        self.blocks["block_1"] = ExampleOne(will_proxy=True)
        self.blocks["block_2"] = ExampleOne(will_proxy=True)

    # IO
    def link_inner_io(self, *args: Any, **kwargs: Any) -> None:
        """Links the inner blocks' IO.

        Args:
            *args: The arguments for creating linking the inner blocks' IO.
            **kwargs: The keyword arguments for creating linking the inner blocks' IO.
        """
        block_1 = self.blocks["block_1"]
        block_2 = self.blocks["block_2"]

        self.inputs.link_forward("one", block_1.inputs, "first")
        self.inputs.link_forward("two", block_1.inputs, "second")
        block_1.outputs.link_forward("out_one", block_2.inputs, "first")
        block_1.outputs.link_forward("out_two", block_2.inputs, "third")
        block_2.outputs.link_forward("out_one", self.outputs, "out_one")
        block_2.outputs.link_forward("out_two", self.outputs, "out_two")



class TestBaseBlock(ClassTest):
    def create_local_block(self):
        return self.ExampleOne()

    def create_proxy_block(self):
        proxy = self.ExampleOne()
        return proxy

    @pytest.fixture(params=[create_local_block, create_proxy_block])
    def test_block(self, request):
        return request.param(self)

    def test_create_block_local(self):
        block = self.ExampleOne(init_setup=True)
        assert block is not None
        assert block.setup_flag

    def test_evaluate_local(self):
        block = self.ExampleOne()
        out_one, out_two = block.evaluate(2, 3, 10)
        assert out_one == 6
        assert out_two == 0

    def test_execute_local(self):
        block = self.ExampleOne()
        block.inputs.put_all(first=2, third=3)
        block.execute()
        outputs = block.outputs.get_all()
        assert outputs["out_one"] == 4
        assert outputs["out_two"] == 12

    # def test_execute_proxy(self):
    #     block = self.ExampleOne()
    #     block.start_server()
    #     block.inputs.put_all(first=2, third=3)
    #     block.execute()
    #     outputs = block.outputs.get_all()
    #     block.stop_server()
    #     assert outputs["out_one"] == 4
    #     assert outputs["out_two"] == 12

    def test_run_local(self):
        block = self.ExampleOne(init_setup=False)
        block.inputs.put_all(first=2, third=3)
        block.run()
        outputs = block.outputs.get_all()
        assert block.setup_flag
        assert block.teardown_flag
        assert outputs["out_one"] == 4
        assert outputs["out_two"] == 12

    def test_run_proxy(self):
        block = self.ExampleOne(will_proxy=True, init_setup=False)
        block.inputs.put_all(first=2, third=3)
        block.run()
        outputs = block.outputs.get_all()

        assert outputs["out_one"] == 4
        assert outputs["out_two"] == 12

        block.update()

        assert block.setup_flag
        assert block.teardown_flag

        block.stop()

    async def local_start_async(self):
        block = self.ExampleOne(init_setup=False)
        block.start()

        await sleep(1)
        block.inputs.put_all(first=2, third=3)
        block.inputs.put_all(first=3, third=2)
        await sleep(0.1)
        outputs_1 = block.outputs.get_all()
        outputs_2 = block.outputs.get_all()
        block.stop()
        await sleep(0.1)
        assert block.setup_flag
        assert block.teardown_flag
        assert outputs_1["out_one"] == 4
        assert outputs_1["out_two"] == 12
        assert outputs_2["out_one"] == 6
        assert outputs_2["out_two"] == 8

    def test_local_start_async(self):
        run(self.local_start_async())

    async def local_start_passive_async(self):
        block = self.ExampleOne(init_setup=False)
        block.start_passive()

        await block.inputs.put_required_callback_async("first", 2)
        await block.inputs.put_required_callback_async("third", 3)
        outputs_1 = await block.outputs.get_all_async()

        await block.stop_passive_async()

        assert block.setup_flag
        assert block.teardown_flag
        assert outputs_1["out_one"] == 4
        assert outputs_1["out_two"] == 12

    def test_local_start_passive_async(self):
        run(self.local_start_passive_async())

    async def local_multiple_start_passive_async(self):
        block1 = self.ExampleOne(init_setup=False)
        block2 = self.ExampleOne(init_setup=False)

        block1.outputs.link_forward("out_one", block2.inputs, "first")
        block1.outputs.link_forward("out_two", block2.inputs, "third")

        block1.start_passive()
        block2.start_passive()

        await block1.inputs.put_required_callback_async("first", 2)
        await block1.inputs.put_required_callback_async("third", 3)
        outputs_1 = await block2.outputs.get_all_async()

        await block1.stop_passive_async()
        await block2.stop_passive_async()

        assert block1.setup_flag
        assert block1.teardown_flag
        assert outputs_1["out_one"] == 8
        assert outputs_1["out_two"] == 48

    def test_local_multiple_start_passive_async(self):
        run(self.local_multiple_start_passive_async())

    def test_start_proxy(self):
        block = self.ExampleOne(will_proxy=True, init_setup=False)
        block.start()
        block.inputs.put_all(first=2, third=3)
        block.inputs.put_all(first=3, third=2)
        outputs_1 = block.outputs.get_all()
        outputs_2 = block.outputs.get_all()

        block.stop()

        assert outputs_1["out_one"] == 4
        assert outputs_1["out_two"] == 12
        assert outputs_2["out_one"] == 6
        assert outputs_2["out_two"] == 8
        assert block.setup_flag
        assert block.teardown_flag

    def test_start_passive_proxy(self):
        DEFAULT_PROCESS_CONTEXT.select_context("multiprocessing")
        group = GroupOne(init_setup=False)
        group.setup()
        group.start_passive()

        group.inputs.put_required_callback("one", 2)
        group.inputs.put_required_callback("two", 3)

        outputs_1 = group.outputs.get_all()

        group.stop_passive()

        assert outputs_1["out_one"] == 4
        assert outputs_1["out_two"] == 12

    def test_multiple_start_passive_proxy(self):
        DEFAULT_PROCESS_CONTEXT.select_context("ray")
        block1 = self.ExampleOne(will_proxy=True, init_setup=False)
        block2 = self.ExampleOne(will_proxy=True, init_setup=False)

        block1.outputs.link_forward("out_one", block2.inputs, "first")
        block1.outputs.link_forward("out_two", block2.inputs, "third")

        block1.inputs.start_server()
        block1.outputs.start_server()
        block2.inputs.start_server()
        block2.outputs.start_server()

        block1.outputs.update_server_io()

        block1.start_passive()
        block2.start_passive()

        block1.inputs.put_required_callback("first", 2)
        block1.inputs.put_required_callback("third", 3)

        outputs_1 = block2.outputs.get_all()

        block1.stop_passive()
        block2.stop_passive()

        assert outputs_1["out_one"] == 8
        assert outputs_1["out_two"] == 48
        assert block1.setup_flag
        assert block1.teardown_flag


# Main #
if __name__ == "__main__":
    # pytest.main(["-v", "-s"])
    t = TestBaseBlock()
    t.test_local_multiple_start_passive_async()
