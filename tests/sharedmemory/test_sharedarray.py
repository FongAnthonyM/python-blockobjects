#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" test_sharedarray.py

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
import numpy as np
import pytest

# Local Packages #
from src.blockobjects.process.sharedmemory.sharedarray.sharedarray import SharedArray


# Definitions #
# Classes #
class TestSharedArray:
    @pytest.mark.parametrize("shape, dtype", [
        ((0,), np.float64),
        ((2, 2), np.int32),
        ((3, 3), np.float64),
        ((4,), np.int8),
        ((2, 3, 4), np.uint16),
    ])
    def test_instance_creation_with_array(self, shape, dtype):
        """Test creating a SharedArray instance with a numpy array."""
        array = np.zeros(shape, dtype=dtype)
        sa = SharedArray(a=array)
        assert sa._array is not None
        assert sa._array.shape == array.shape
        assert sa._array.dtype == array.dtype
        sa.unlink()

    @pytest.mark.parametrize("shape, dtype", [
        ((0,), np.float64),
        ((2, 2), np.int32),
        ((3, 3), np.float64),
        ((4,), np.int8),
        ((2, 3, 4), np.uint16),
    ])
    def test_instance_creation_with_shape(self, shape, dtype):
        """Test creating a SharedArray instance with a shape."""
        sa = SharedArray(shape=shape, dtype=dtype)
        assert sa._array is not None
        assert sa._array.shape == shape
        assert sa._array.dtype == dtype
        sa.unlink()

    def test_array_function_execution(self):
        """Test numpy array function execution with SharedArray."""
        array = np.array([1, 2, 3], dtype=np.int32)
        sa = SharedArray(a=array)
        result = np.sum(sa)
        assert result == 6

    def test_copy_array(self):
        """Test copying the contents from SharedArray to a regular numpy array."""
        array = np.array([1, 2, 3], dtype=np.int32)
        sa = SharedArray(a=array)
        copied_array = sa.copy_array()
        assert np.array_equal(copied_array, array)
        assert isinstance(copied_array, np.ndarray)


# Main #
if __name__ == "__main__":
    pytest.main(["-v", "-s"])
