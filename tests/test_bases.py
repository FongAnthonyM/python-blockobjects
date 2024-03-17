#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" test_baseobjects.py

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
import pathlib

# Third-Party Packages #
import pytest

# Local Packages #


# Definitions #
# Functions #
@pytest.fixture
def tmp_dir(tmpdir):
    """A pytest fixture that turn the tmpdir into a Path object."""
    return pathlib.Path(tmpdir)


# Classes #
class ClassTest(abc.ABC):
    """Default class tests that all classes should pass."""

    class_ = None

    def test_instance_creation(self, *args, **kwargs):
        pass


# Main #
if __name__ == "__main__":
    pytest.main(["-v", "-s"])
