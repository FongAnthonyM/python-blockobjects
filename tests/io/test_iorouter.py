#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" test_baseobjects.py

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
from src.blockobjects.process.context.multiprocessingcontext import MultiProcessingContext
from src.blockobjects.io import IORouter
from tests.test_bases import ClassTest


# Definitions #
if DEFAULT_PROCESS_CONTEXT.context is None:
    DEFAULT_PROCESS_CONTEXT.select_context("multiprocessing")


# Classes #
class TestIORouter(ClassTest):
    context_type = MultiProcessingContext

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

    def create_iorouter(self):
        context = self.get_context()
        return IORouter(context=context)

    @pytest.fixture(params=[create_manger_context])
    def test_context(self, request):
        return request.param(self)

    @pytest.fixture(params=[create_iorouter])
    def test_iorouter(self, request):
        return request.param(self)

    def test_create_iorouter(self):
        assert IORouter() is not None

    def test_put_get(self):
        io_router = IORouter(names=("first", "second", "third", "fourth"))
        io_router.put(10)
        items = io_router.get()
        assert items == {"first": 10, "second": 10, "third": 10, "fourth": 10}

    def test_get_all_required(self):
        io_router = IORouter(names=("first", "second", "third", "fourth"))
        io_router.put_all({"first": 1, "third": 3})
        items = io_router.get_all_required(("first", "third"), default=None)
        assert items == {"first": 1, "second": None, "third": 3, "fourth": None}

    async def get_all_required_async(self):
        io_router = IORouter(names=("first", "second", "third", "fourth"))
        await io_router.put_all_async({"first": 1, "third": 3})
        items = await io_router.get_all_required_async(("first", "third"), default=None)
        assert items == {"first": 1, "second": None, "third": 3, "fourth": None}

    def test_get_all_required_async(self):
        run(self.get_all_required_async())

    def test_get_all_required_defaults(self):
        io_router = IORouter(names=("first", "second", "third", "fourth"))
        io_router.put_all({"first": 1, "third": 3})
        items = io_router.get_all_required(("first", "third"), defaults={"second": 2, "fourth": 4})
        assert items == {"first": 1, "second": 2, "third": 3, "fourth": 4}

    async def get_all_required_defaults_async(self):
        io_router = IORouter(names=("first", "second", "third", "fourth"))
        await io_router.put_all_async({"first": 1, "third": 3})
        items = await io_router.get_all_required_async(("first", "third"), defaults={"second": 2, "fourth": 4})
        assert items == {"first": 1, "second": 2, "third": 3, "fourth": 4}

    def test_get_all_required_defaults_async(self):
        run(self.get_all_required_defaults_async())


# Main #
if __name__ == "__main__":
    pytest.main(["-v", "-s"])
