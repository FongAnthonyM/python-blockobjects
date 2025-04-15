""" sharedarray.py
A wrapper for a numpy ndarray which allocates it in SharedMemory.
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
from collections.abc import Iterable, Mapping
from multiprocessing.shared_memory import SharedMemory
from typing import Any
from warnings import warn

# Third-Party Packages #
from baseobjects import BaseReducible
from baseobjects.wrappers import StaticWrapper
import numpy as np

# Local Packages #


# Definitions #
# Classes #
class SharedArray(StaticWrapper, BaseReducible):
    """A wrapper for a numpy ndarray which allocates it in SharedMemory.

    Class Attributes:
        shared_memory_type: The type of SharedMemory this class will use in its instances.

    Attributes:
        _offset: The offset of array data in the buffer.
        _array: The ndarray which this object is wrapping.
        _shared_memory: The SharedMemory which the array is allocated to.

    Args:
        a: An optional array to set the values of this array to.
        shape: The shape to set the array to.
        name: The shared memory name.
        dtype: The data type of the array.
        offset: The offset of array data in the buffer.
        strides: The strides of data in memory
        order: Row-major (C-style) or column-major (Fortran-style) order.
        override: Determines if the existing data in a loaded SharedMemory should be replaced with the new data.
        load_only: Determines if the array should be loaded from the SharedMemory. If True, the array will be loaded
            from the SharedMemory but not created.
        init: Determines if this object should be initialized.
    """

    _wrapped_types: list[type | object] = [np.ndarray]
    _wrap_attributes: list[str] = ["array"]
    _exclude_attributes: set[str] = StaticWrapper._exclude_attributes | {"__array_ufunc__"}
    shared_memory_type: type[SharedMemory] = SharedMemory

    _offset: int = 0
    _array: np.ndarray | None = None
    _shared_memory: SharedMemory | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        a: np.ndarray | None = None,
        shape: Iterable[int, ...] | None = None,
        name: str | None = None,
        dtype: str | np.dtype | None = None,
        offset: int = 0,
        strides: Iterable[int, ...] | None = None,
        order: str | None = None,
        override: bool = False,
        *,
        load_only: bool = False,
        init: bool = True,
    ) -> None:
        # Parent Attributes #
        super().__init__(init=False)

        # Construct #
        if init:
            self.construct(
                a=a,
                shape=shape,
                name=name,
                dtype=dtype,
                offset=offset,
                strides=strides,
                order=order,
                override=override,
                load_only=load_only
            )

    @property
    def name(self) -> str:
        """The SharedMemory name."""
        return self._shared_memory.name

    # Pickling
    def __getstate__(self) -> None | dict[str, Any] | tuple[dict[str, Any] | None, dict[str, Any]]:
        """Gets the object's state for pickling.

        Returns:
            The state returned will be either of the following types based on the presence of __dict__ and __slots__:
                None: __dict__ nor __slots__ are present.
                dict: __dict__ is present and __slots__ is not present.
                tuple[None, dict]: __dict__ is not present and __slots__ is present.
                tuple[dict, dict]: __dict__ is present and __slots__ is present.
        """
        state = self.__getstate__()
        state["_array"] = None
        state["_shared_memory"] = None
        state["kwargs"] = {
            "name": self._shared_memory.name,
            "shape": self._array.shape,
            "dtype": self._array.dtype,
            "offset": self._offset,
            "strides": self._array.strides,
            "order": "C" if self._array.flags.c_contiguous else "F",
        }

        return state

    def __setstate__(self, state: Any) -> None:
        """Sets the object's state from a pickled state.

        By default, the state can be one of the following types with the corresponding behavior:
            None: Will not set any state.
            dict: Will set the __dict__ attribute to the state.
            tuple[None, dict]: Will set the slot values to the second dict of the tuple.
            tuple[dict, dict]: Will set the __dict__ attribute to the first dict of the tuple and set the slot values
                to the second dict of the tuple.

        Args:
            state: An object which can be used to set the state of this object.
        """
        kwargs = state.pop("kwargs")
        self.__setstate__(state)

        self.construct_existing_array(**kwargs)

    # Array
    def __array_function__(self, func, types, args, kwargs) -> Any:
        """Handles how numpy functions are executed with this object.

        Args:
            func: The function to execute.
            types: The types of the args and kwargs.
            args: The arguments to the function.
            kwargs: The keyword arguments to the function.

        Returns:
            The result of the numpy function
        """
        return func(
            *(self._array if arg is self else arg for arg in args),
            **{k: self._array if v is self else v for k, v in kwargs.items()},
        )

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        a: np.ndarray | None = None,
        shape: Iterable[int, ...] | None = None,
        name: str | None = None,
        dtype: str | np.dtype | None = None,
        offset: int | None = None,
        strides: Iterable[int, ...] | None = None,
        order: str | None = None,
        override: bool = False,
        *,
        load_only: bool = False,
    ) -> None:
        """Constructs this object.

        Args:
            a: An optional array to set the values of this array to.
            shape: The shape to set the array to.
            name: The shared memory name.
            dtype: The data type of the array.
            offset: The offset of array data in the buffer.
            strides: The strides of data in memory
            order: Row-major (C-style) or column-major (Fortran-style) order.
            override: Determines if the existing data in a loaded SharedMemory should be replaced with the new data.
            load_only: Determines if the array should be loaded from the SharedMemory. If True, the array will be loaded
                from the SharedMemory but not created.
        """
        if a is not None:
            self.construct_from_array(a, name, override=override)
        elif shape is not None:
            if load_only:
                self.construct_existing_array(
                    shape=shape,
                    name=name,
                    dtype=dtype,
                    offset=offset,
                    strides=strides,
                    order=order,
                )
            else:
                self.construct_new_array(
                    shape=shape,
                    name=name,
                    dtype=dtype,
                    offset=offset,
                    strides=strides,
                    order=order,
                )
        elif name is not None:
            raise ValueError("Either an array or the shape must be provided.")

    def construct_from_array(self, a: np.ndarray, name: str | None = None, override: bool = False) -> None:
        """Constructs this object from a given array. Replaces the values if the SharedMemory already exists.

        Args:
            a: The array to set the values this array to.
            name: The name of this SharedMemory.
            override: Determines if the existing data in a loaded SharedMemory should be replaced with the new data.
        """
        try:
            self._shared_memory = self.shared_memory_type(name=name, create=True, size=int(a.nbytes))
        except ValueError as error:
            if int(a.nbytes) == 0:
                self._array = np.ndarray(a.shape, dtype=a.dtype)
                if self._shared_memory is not None:
                    del self._shared_memory
            else:
                raise error
        except FileExistsError:
            self._shared_memory = self.shared_memory_type(name=name)
            self._array = np.ndarray(a.shape, dtype=a.dtype, buffer=self._shared_memory.buf)
            if override:
                warn(f"SharedMemory '{name}' already exists. Replacing existing data.", RuntimeWarning)
                self[:] = a[:]
            else:
                warn(f"SharedMemory '{name}' already exists. Loading existing data.", RuntimeWarning)
        else:
            self._array = np.ndarray(a.shape, dtype=a.dtype, buffer=self._shared_memory.buf)
            self[:] = a[:]

    def construct_new_array(
        self,
        shape: Iterable[int, ...],
        name: str | None = None,
        dtype: str | np.dtype | None = None,
        offset: int = 0,
        strides: Iterable[int, ...] | None = None,
        order: str | None = None,
    ) -> None:
        """Constructs this object from given parameters.

        Args:
            shape: The shape to set the array to.
            name: The shared memory name.
            dtype: The data type of the array.
            offset: The offset of array data in the buffer.
            strides: The strides of data in memory
            order: Row-major (C-style) or column-major (Fortran-style) order.
        """
        try:
            self._shared_memory = self.shared_memory_type(
                name=name,
                create=True,
                size=int(np.dtype(dtype).itemsize * np.prod(shape)),
            )
        except ValueError as error:
            if int(np.dtype(dtype).itemsize * np.prod(shape)) == 0:
                self._array = np.ndarray(shape, dtype=dtype)
                if self._shared_memory is not None:
                    del self._shared_memory
            else:
                raise error
        except FileExistsError:
            self._shared_memory = self.shared_memory_type(name=name)
            self._array = np.ndarray(
                shape,
                dtype=dtype,
                buffer=self._shared_memory.buf,
                offset=offset,
                strides=strides,
                order=order,
            )
        else:
            self._array = np.ndarray(
                shape,
                dtype=dtype,
                buffer=self._shared_memory.buf,
                offset=offset,
                strides=strides,
                order=order,
            )

    def construct_existing_array(
        self,
        shape: Iterable[int, ...],
        name: str | None = None,
        dtype: str | np.dtype | None = None,
        offset: int = 0,
        strides: Iterable[int, ...] | None = None,
        order: str | None = None,
    ) -> None:
        """Constructs this object from given parameters.

        Args:
            shape: The shape to set the array to.
            name: The shared memory name.
            dtype: The data type of the array.
            offset: The offset of array data in the buffer.
            strides: The strides of data in memory
            order: Row-major (C-style) or column-major (Fortran-style) order.
        """
        self._shared_memory = self.shared_memory_type(name=name)

        self._array = np.ndarray(
            shape,
            dtype=dtype,
            buffer=self._shared_memory.buf,
            offset=offset,
            strides=strides,
            order=order,
        )

    def copy_array(self) -> np.ndarray:
        """Copies the array to a ndarray not it SharedMemory.

        Returns:
            A new copy not in SharedMemory.
        """
        return self._array.copy()

    # Shared Memory
    def close(self) -> None:
        """Closes access to the shared memory from this instance but does not destroy the shared memory block."""
        if self._shared_memory is not None:
            self._shared_memory.close()

    def unlink(self) -> None:
        """Requests that the underlying shared memory block be destroyed.

        In order to ensure proper cleanup of resources, unlink should be called once (and only once) across all
        processes which have access to the shared memory block.
        """
        if self._shared_memory is not None:
            self._shared_memory.unlink()
