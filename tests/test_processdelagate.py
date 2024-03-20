#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" test_processdelgate.py
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
from asyncio import sleep, run
import pickle
from os import getpid

# Third-Party Packages #
import pytest

# Local Packages #
from src.blockobjects.process.context import DEFAULT_PROCESS_CONTEXT, ManagerContext
from src.blockobjects.process.multiprocessing import MultiProcessingContext
from src.blockobjects.process.processdelegate import ProcessDelegate
from .test_bases import ClassTest


# Definitions #
# Classes #
class BaseProcessDelegateTest(ClassTest):
    class BaseExampleOne:

        # Class Attributes #
        exposed = {"_available"}
        unexposed = {"unavailable"}

        # Attributes #
        one: int = 1
        item: int = 10

        def __init__(self, one=1, item=10, *args, **kwargs):
            self.one = one
            self.item = item

            super().__init__(*args, **kwargs)

        def running_pid(self):
            return getpid()

        def _unavailable(self):
            return getpid()

        def unavailable(self):
            return getpid()

        def _available(self):
            return "available"

        async def quick_async(self):
            return "fast"

        async def active_async(self):
            await sleep(0.000000001)
            return "active"

        def multiply(self, num) -> float:
            return float(self.one * num)

    context_type = None

    def create_context(self):
        return self.context_type()

    def create_manger_context(self):
        manger_context = ManagerContext()
        manger_context.contexts["test"] = self.create_context()
        manger_context.select_context("test")
        return manger_context

    def get_context(self):
        if self.context_type is None:
            return DEFAULT_PROCESS_CONTEXT
        else:
            return self.create_manger_context()

    def create_local_processdelegate(self):
        return self.ExampleOne(context=self.create_manger_context())

    def create_proxy_processdelegate(self):
        proxy = self.ExampleOne(start_server=True, context=self.create_manger_context())
        return proxy

    @pytest.fixture(params=[create_manger_context])
    def test_context(self, request):
        return request.param(self)

    @pytest.fixture(params=[create_local_processdelegate, create_proxy_processdelegate])
    def test_processdelegate(self, request):
        return request.param(self)

    def test_create_local_delegate(self):
        delegate = self.ExampleOne(context=self.create_manger_context())
        assert delegate is not None

    def test_start_server(self):
        delegate = self.ExampleOne(context=self.create_manger_context())
        delegate.start_server()

        assert delegate.is_proxy()
        assert delegate.is_alive()

        delegate.stop_server()

    def test_stop_server(self):
        delegate = self.ExampleOne(context=self.create_manger_context())
        delegate.start_server()

        assert delegate.is_proxy()
        assert delegate.is_alive()

        delegate.stop_server()

        assert not delegate.is_proxy()
        assert not delegate.is_alive()

    def test_start_server_init(self):
        delegate = self.ExampleOne(start_server=True, context=self.create_manger_context())
        assert delegate.is_proxy()
        assert delegate.is_alive()

        delegate.stop_server()

        assert not delegate.is_proxy()
        assert not delegate.is_alive()

    def test_processdelegate_call(self, test_processdelegate):
        if test_processdelegate.is_proxy():
            assert test_processdelegate.running_pid() != getpid()
        else:
            assert test_processdelegate.running_pid() == getpid()

    def test_exposed_call(self, test_processdelegate):
        assert test_processdelegate._available() == "available"

    def test_unexposed_calls(self, test_processdelegate):
        assert test_processdelegate._unavailable() == getpid()
        assert test_processdelegate.unavailable() == getpid()

    async def quick_async(self, test_processdelegate):
        answer = await test_processdelegate.quick_async()
        assert answer == "fast"

    def test_quick_async(self, test_processdelegate):
        run(self.quick_async(test_processdelegate))

    async def active_async(self, test_processdelegate):
        future = test_processdelegate.active_async()
        if hasattr(future, "done"):
            assert not future.done()
        answer = await future
        assert answer == "active"

    def test_active_async(self, test_processdelegate):
        run(self.active_async(test_processdelegate))

    def test_get_attribute(self, test_processdelegate):
        assert test_processdelegate.get_attribute("one") == 1
        assert test_processdelegate.get_attribute("one", None) == 1
        assert test_processdelegate.get_attribute("none", None) is None
        try:
            test_processdelegate.get_attribute("none")
        except AttributeError:
            assert True
        else:
            assert False, "Should throw an AttributeError"

    def test_set_attribute(self, test_processdelegate):
        test_processdelegate.set_attribute("item", 1000)
        assert test_processdelegate.get_attribute("item") == 1000

    def test_init_state_passing(self):
        delegate = self.ExampleOne(one=2, context=self.create_manger_context())
        delegate.start_server()
        assert delegate.get_attribute("one") == 2

    def test_stop_state_passing(self):
        delegate = self.ExampleOne(context=self.create_manger_context())
        delegate.start_server()
        delegate.set_attribute("item", 2)
        delegate.stop_server()
        assert delegate.item == 2

    def test_update_server(self):
        delegate = self.ExampleOne(context=self.create_manger_context())
        delegate.start_server()
        delegate.item = 2
        delegate.update_server()
        assert delegate.get_attribute("item") == 2
        delegate.stop_server()


class TestProcessDelegate(BaseProcessDelegateTest):

    class ExampleOne(BaseProcessDelegateTest.BaseExampleOne, ProcessDelegate):
        """A mixin class that is a ProcessDelegate and example class for testing."""

    context_type = MultiProcessingContext


# Main #
if __name__ == "__main__":
    pytest.main(["-v", "-s"])
