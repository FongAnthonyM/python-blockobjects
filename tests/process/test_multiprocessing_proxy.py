#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" test_baseobjects.py
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
from src.blockobjects.process.context.multiprocessingcontext import MultiProcessingContext
from .test_proxy import BaseProxyTest


# Definitions #
# Classes #
class TestMultiprocessingProxy(BaseProxyTest):
    context_type = MultiProcessingContext


# Main #
if __name__ == "__main__":
    pytest.main(["-v", "-s"])
