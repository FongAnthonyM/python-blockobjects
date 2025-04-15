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

# Third-Party Packages #
import pytest

# Local Packages #
from src.blockobjects.process.context.raycontext import RayContext
from .test_proxy import BaseProxyTest


# Definitions #
# Classes #
class TestRayProxy(BaseProxyTest):
    context_type = RayContext


# Main #
if __name__ == "__main__":
    pytest.main(["-v", "-s"])
