#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" test_baseobjects.py
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

# Third-Party Packages #
import pytest

# Local Packages #
from src.blockobjects.process.ray import context
from .test_proxy import BaseProxyTest


# Definitions #
# Classes #
class TestRayProxy(BaseProxyTest):
    context_type = context


# Main #
if __name__ == "__main__":
    pytest.main(["-v", "-s"])
