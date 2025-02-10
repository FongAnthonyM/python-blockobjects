""" baseblock.py.py

"""
# Package Header #
from ...header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Standard Libraries #
from abc import abstractmethod
from itertools import chain
from typing import ClassVar, Any
from uuid import uuid4

# Third-Party Packages #

# Local Packages #
from .baseblock import BaseBlock


# Definitions #
# Classes #
class BaseProducerBlock(BaseBlock):
    """An abstract base class for producer blocks."""

    # Attributes #
    will_produce = True

    # Output
    def format_output(
        self,
        outputs: Any,
        ids: dict[str, Any] | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> dict[str, Any] | None:
        new_ids = (uuid4().bytes,) if ids is None else tuple(set(chain.from_iterable(ids.values())))
        return self._format_output(outputs, ids=new_ids, *args, **kwargs)

    # Evaluate
    @abstractmethod
    def evaluate(self, *args, input_ids: dict[str, tuple[bytes, ...]] | None = None, **kwargs: Any) -> Any:
        """An abstract method which is the evaluation of this object.

        Args:
            *args: The arguments for evaluating.
            input_ids: The ids of the inputs.
            **kwargs: The keyword arguments for evaluating.

        Returns:
            The result of the evaluation.
        """
