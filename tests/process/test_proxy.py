#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""test_proxy.py
Test for the baseobjects package.

"""

# Header #
__package_name__ = "blockobjects"

__author__ = "Anthony Fong"
__credits__ = ["Anthony Fong"]
__copyright__ = "Copyright 2022, Anthony Fong"
__license__ = "MIT"

__version__ = "0.1.0"


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
from tests.test_bases import ClassTest


# Definitions #
# Classes #
class BaseProxyTest(ClassTest):
    class ExampleOne:

        exposed = set(("_available",))
        unexposed = set(("unavailable",))

        def __init__(self):
            self.one = "one"
            self.two = "one"

        def __eq__(self, other):
            return True

        def running_pid(self):
            return getpid()

        def _unavailable(self):
            return "unavailable"

        def unavailable(self):
            return "unavailable"

        def _available(self):
            return "available"

        async def quick_async(self):
            return "fast"

        async def active_async(self):
            await sleep(0.0000001)
            return "active"

    class ExampleTwo:
        def __init__(self):
            self.one = "two"
            self.three = "two"

        def function(self):
            return "two"

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

    def create_proxy(self):
        context = self.get_context()
        return context.create_proxy(cls=self.ExampleOne, args=(), kwargs={})

    @pytest.fixture(params=[create_manger_context])
    def test_context(self, request):
        return request.param(self)

    @pytest.fixture(params=[create_proxy])
    def test_proxy(self, request):
        return request.param(self)

    def test_create_proxy(self, test_context):
        proxy = test_context.create_proxy(cls=self.ExampleOne, args=(), kwargs={})
        assert proxy is not None

    def test_proxy_call(self, test_proxy):
        assert test_proxy.running_pid() != getpid()

    def test_exposed_call(self, test_proxy):
        assert test_proxy._available() == "available"

    def test_unexposed_calls(self, test_proxy):
        try:
            test_proxy._unavailable()
        except AttributeError:
            assert not hasattr(test_proxy, "_unavailable")
        else:
            assert False, "Unexposed method was available."

        try:
            test_proxy.unavailable()
        except AttributeError:
            assert not hasattr(test_proxy, "unavailable")
        else:
            assert False, "Unexposed method was available."

    async def quick_async(self, test_proxy):
        answer = await test_proxy.quick_async()
        assert answer == "fast"

    def test_quick_async(self, test_proxy):
        run(self.quick_async(test_proxy))

    async def active_async(self, test_proxy):
        awaitable = test_proxy.active_async()
        if (done_method := getattr(awaitable, "done", None)) is not None:
            assert not done_method()

        answer = await awaitable
        assert answer == "active"

    def test_active_async(self, test_proxy):
        run(self.active_async(test_proxy))


# Main #
if __name__ == "__main__":
    pytest.main(["-v", "-s"])
