#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" block_baseobjects.py
Test for the baseobjects package.
"""
# Package Header #
from src.blockobjects.header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Standard Libraries #
import abc
from asyncio import sleep, run
import copy
import cProfile
import pathlib
import io
import pstats
from pstats import Stats, f8, func_std_string
import timeit
import time
from typing import Any

# Third-Party Packages #
import pytest

# Local Packages #
from src.blockobjects.process import DEFAULT_PROCESS_CONTEXT
from src.blockobjects.process.context import ManagerContext
from src.blockobjects.process.multiprocessing import MultiProcessingContext
from src.blockobjects.process.processdelegate import ProcessDelegate
from src.blockobjects.blocks import BaseBlock
from src.rayblocks import RayContext

# Definitions #
DEFAULT_PROCESS_CONTEXT.select_context("multiprocessing")


# Functions #
@pytest.fixture
def tmp_dir(tmpdir):
    """A pytest fixture that turn the tmpdir into a Path object."""
    return pathlib.Path(tmpdir)


# Classes #
class StatsMicro(Stats):
    def print_stats(self, *amount):
        for filename in self.files:
            print(filename, file=self.stream)
        if self.files:
            print(file=self.stream)
        indent = " " * 8
        for func in self.top_level:
            print(indent, func_get_function_name(func), file=self.stream)

        print(indent, self.total_calls, "function calls", end=" ", file=self.stream)
        if self.total_calls != self.prim_calls:
            print("(%d primitive calls)" % self.prim_calls, end=" ", file=self.stream)
        print("in %.3f microseconds" % (self.total_tt * 1000000), file=self.stream)
        print(file=self.stream)
        width, list = self.get_print_list(amount)
        if list:
            self.print_title()
            for func in list:
                self.print_line(func)
            print(file=self.stream)
            print(file=self.stream)
        return self

    def print_line(self, func):  # hack: should print percentages
        cc, nc, tt, ct, callers = self.stats[func]
        c = str(nc)
        if nc != cc:
            c = c + "/" + str(cc)
        print(c.rjust(9), end=" ", file=self.stream)
        print(f8(tt * 1000000), end=" ", file=self.stream)
        if nc == 0:
            print(" " * 8, end=" ", file=self.stream)
        else:
            print(f8(tt / nc * 1000000), end=" ", file=self.stream)
        print(f8(ct * 1000000), end=" ", file=self.stream)
        if cc == 0:
            print(" " * 8, end=" ", file=self.stream)
        else:
            print(f8(ct / cc * 1000000), end=" ", file=self.stream)
        print(func_std_string(func), file=self.stream)


class PerformanceTest(abc.ABC):
    """Default tests that all classes should pass."""

    timeit_runs = 100000
    speed_tolerance = 200
    call_speed = timeit.timeit(lambda: None, number=10000000) / 10000000 * 1000000


class TestBaseBlock(PerformanceTest):

    class ExampleOne(BaseBlock):
        # Class Attributes #
        default_input_names = ("first", "second", "third", "fourth")
        default_required_input = ("first", "third")
        default_optional_input = {"second": 2, "fourth": 4}
        default_output_names = ("out_one", "out_two")
        proxy_kwargs = {"ray": {"num_cpus": 1}}

        # Attributes #
        setup_flag: bool = False
        teardown_flag: bool = False

        # Setup
        def setup(self, *args: Any, **kwargs: Any) -> None:
            """A method for setting up the object."""
            self.setup_flag = True

        # Evaluate
        def evaluate(self, first=1, second=0, third=1, fourth=0) -> Any:
            # deadline = time.perf_counter() + 1
            # while deadline >= time.perf_counter():
            #     pass
            return first, third

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

    def test_create_block_local(self):
        block = self.ExampleOne(init_setup=True)
        assert block is not None
        assert block.setup_flag

    def test_evaluate_local(self):
        block = self.ExampleOne()
        out_one, out_two = block.evaluate(2, 3, 10)
        assert out_one == 6
        assert out_two == 0

    def test_execute_local_profile(self):
        block = self.ExampleOne()
        block.inputs.put_all(first=2, third=3)
        pr = cProfile.Profile()
        pr.enable()

        block.execute()

        pr.disable()
        s = io.StringIO()
        sortby = pstats.SortKey.TIME
        ps = StatsMicro(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())

        outputs = block.outputs.get_all()

    def test_execute_proxy(self):
        block = self.ExampleOne()
        block.start_server()
        block.inputs.put_all(first=2, third=3)
        block.execute()
        outputs = block.outputs.get_all()
        block.stop_server()
        assert outputs["out_one"] == 4
        assert outputs["out_two"] == 12

    def test_run_local_profile(self):
        block = self.ExampleOne(init_setup=False)
        block.inputs.put_all(first=2, third=3)
        pr = cProfile.Profile()
        pr.enable()

        block.run()

        pr.disable()
        s = io.StringIO()
        sortby = pstats.SortKey.TIME
        ps = StatsMicro(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())

        outputs = block.outputs.get_all()

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
        block.inputs.put_all(first=2, third=3)
        block.inputs.put_all(first=3, third=2)
        await sleep(0.2)
        outputs_1 = block.outputs.get_all()
        outputs_2 = block.outputs.get_all()
        block.stop()
        await sleep(0.001)
        assert block.setup_flag
        assert block.teardown_flag
        assert outputs_1["out_one"] == 4
        assert outputs_1["out_two"] == 12
        assert outputs_2["out_one"] == 6
        assert outputs_2["out_two"] == 8

    def test_local_start_async(self):
        run(self.local_start_async())

    async def local_start_passive_async_profile(self):
        block = self.ExampleOne(init_setup=False)
        block.start_passive()

        pr = cProfile.Profile()
        pr.enable()

        await block.inputs.put_required_callback_async("first", 2)
        await block.inputs.put_required_callback_async("third", 3)
        outputs_1 = await block.outputs.get_all_async()

        pr.disable()

        await block.stop_passive_async()

        s = io.StringIO()
        sortby = pstats.SortKey.TIME
        ps = StatsMicro(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())

    def test_local_start_passive_async_profile(self):
        run(self.local_start_passive_async_profile())

    async def local_multiple_start_passive_async_profile(self):
        block1 = self.ExampleOne(init_setup=False)
        block2 = self.ExampleOne(init_setup=False)

        block1.outputs.link_forward("out_one", block2.inputs, "first")
        block1.outputs.link_forward("out_two", block2.inputs, "third")

        block1.start_passive()
        block2.start_passive()

        pr = cProfile.Profile()
        pr.enable()

        await block1.inputs.put_required_callback_async("first", 2)
        await block1.inputs.put_required_callback_async("third", 3)
        outputs_1 = await block2.outputs.get_all_async()

        pr.disable()

        await block1.stop_passive_async()
        await block2.stop_passive_async()

        s = io.StringIO()
        sortby = pstats.SortKey.TIME
        ps = StatsMicro(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())

    def test_local_multiple_start_passive_async_profile(self):
        run(self.local_multiple_start_passive_async_profile())

    def test_io_evaluate_profile(self):
        block = self.ExampleOne(init_setup=False)

        pr = cProfile.Profile()
        pr.enable()

        block.evaluate(first=2, third=3)

        pr.disable()
        s = io.StringIO()
        sortby = pstats.SortKey.TIME
        ps = StatsMicro(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())

    def test_io_start_profile(self):
        DEFAULT_PROCESS_CONTEXT.select_context("multiprocessing")
        block = self.ExampleOne(will_proxy=True, init_setup=False)
        block.start()

        pr = cProfile.Profile()
        pr.enable()

        block.inputs.put_all(first=2, third=3)
        outputs_1 = block.outputs.get_all()

        pr.disable()
        block.stop_passive()
        s = io.StringIO()
        sortby = pstats.SortKey.TIME
        ps = StatsMicro(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())

    def test_io_start_passive_profile(self):
        DEFAULT_PROCESS_CONTEXT.select_context("ray")
        block = self.ExampleOne(will_proxy=True, init_setup=False)
        block.start_passive()

        pr = cProfile.Profile()
        pr.enable()

        block.inputs.put_required_callback("first", 2)
        block.inputs.put_required_callback("third", 3)

        outputs_1 = block.outputs.get_all()

        pr.disable()
        block.stop_passive()
        s = io.StringIO()
        sortby = pstats.SortKey.TIME
        ps = StatsMicro(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())

    def test_io_multiple_start_passive_profile(self):
        DEFAULT_PROCESS_CONTEXT.select_context("multiprocessing")
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

        pr = cProfile.Profile()
        pr.enable()

        block1.inputs.put_required_callback("first", 2)
        block1.inputs.put_required_callback("third", 3)
        outputs_1 = block2.outputs.get_all()

        pr.disable()
        block1.stop_passive()
        block2.stop_passive()
        s = io.StringIO()
        sortby = pstats.SortKey.TIME
        ps = StatsMicro(pr, stream=s).sort_stats(sortby)
        ps.print_stats()
        print(s.getvalue())


# Main #
if __name__ == "__main__":
    # pytest.main(["-v", "-s"])
    t = TestBaseBlock()
    t.test_local_multiple_start_passive_async_profile()
