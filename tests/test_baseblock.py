#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" test_baseblock.py
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

# Local Packages #
from src.blockobjects.process import DEFAULT_PROCESS_CONTEXT
from src.blockobjects.process.context import ManagerContext
from src.blockobjects.process.multiprocessing import MultiProcessingContext
from src.blockobjects.process.processdelegate import ProcessDelegate
from src.blockobjects.blocks import BaseBlock
from .test_bases import ClassTest


# Definitions #
if DEFAULT_PROCESS_CONTEXT.context is None:
    DEFAULT_PROCESS_CONTEXT.select_context("multiprocessing")


# Classes #
class TestBaseBlock(ClassTest):

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

        # Evaluate
        def evaluate(self, first=1, second=0, third=1, fourth=0) -> Any:
            out_one = first * second
            out_two = third * fourth
            return out_one, out_two

        # Teardown
        def teardown(self, *args: Any, **kwargs: Any) -> None:
            """A method for setting up the object."""
            self.teardown_flag = True

    def create_local_block(self):
        return self.ExampleOne()

    def create_proxy_block(self):
        proxy = self.ExampleOne()
        return proxy

    @pytest.fixture(params=[create_local_block, create_proxy_block])
    def test_block(self, request):
        return request.param(self)

    def test_create_local_block(self):
        block = self.ExampleOne(init_setup=True)
        assert block is not None
        assert block.setup_flag

    def test_local_evaluate(self):
        block = self.ExampleOne()
        out_one, out_two = block.evaluate(2, 3, 10)
        assert out_one == 6
        assert out_two == 0

    def test_local_execute(self):
        block = self.ExampleOne()
        block.inputs.put_all(first=2, third=3)
        block.execute()
        outputs = block.outputs.get_all()
        assert outputs["out_one"] == 4
        assert outputs["out_two"] == 12

    def test_local_run(self):
        block = self.ExampleOne(init_setup=False)
        block.inputs.put_all(first=2, third=3)
        block.run()
        outputs = block.outputs.get_all()
        assert block.setup_flag
        assert block.teardown_flag
        assert outputs["out_one"] == 4
        assert outputs["out_two"] == 12

    async def local_start_async(self):
        block = self.ExampleOne(init_setup=False)
        block.start()
        block.inputs.put_all(first=2, third=3)
        block.inputs.put_all(first=3, third=2)
        await sleep(0.3)
        outputs_1 = block.outputs.get_all()
        outputs_2 = block.outputs.get_all()
        block.stop()
        await sleep(1.0)
        assert block.setup_flag
        assert block.teardown_flag
        assert outputs_1["out_one"] == 4
        assert outputs_1["out_two"] == 12
        assert outputs_2["out_one"] == 6
        assert outputs_2["out_two"] == 8

    def test_local_start_async(self):
        run(self.local_start_async())

    def test_proxy_execute(self):
        block = self.ExampleOne()
        block.start_server()
        block.inputs.put_all(first=2, third=3)
        block.execute()
        outputs = block.outputs.get_all()
        block.stop_server()
        assert outputs["out_one"] == 4
        assert outputs["out_two"] == 12






# Main #
if __name__ == "__main__":
    pytest.main(["-v", "-s"])
