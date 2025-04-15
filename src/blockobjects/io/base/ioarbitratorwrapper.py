""" ioarbitratorwrapper.py
An IO Object which wraps a ProcessArbitrator as an IO Object.
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
from typing import Any

# Third-Party Packages #
from baseobjects import BaseReducible
from ...process import ProcessArbitrator

# Local Packages #
from .baseio import BaseIO


# Definitions #
# Classes #
class IOArbitratorWrapper(BaseIO, BaseReducible):
    """An IO Object which wraps a ProcessArbitrator as an IO Object.

    Attributes:
        use_proxy: Determines, when pickling, if the arbitrator should only provide the proxy or the actual object.
        arbitrator: The ProcessArbitrator instance that provides the methods to be wrapped.
        getter: The name of a function or method within the arbitrator to be used for getting data.
        getter_async: The name of an asynchronous function or method within the arbitrator to be used for getting data.
        putter: The name of a function or method within the arbitrator to be used for putting data.
        putter_async: The name of an asynchronous function or method within the arbitrator to be used for putting data.
        joiner: The name of a function or method within the arbitrator to be used for joining.
        joiner_async: The name of an asynchronous function or method within the arbitrator to be used for joining.

    Args:
        arbitrator: A ProcessArbitrator instance that provides the methods to be wrapped.
        getter: The name of a function or method within the arbitrator to be used for getting data.
        getter_async: The name of an asynchronous function or method within the arbitrator to be used for getting data.
        putter: The name of a function or method within the arbitrator to be used for putting data.
        putter_async: The name of an asynchronous function or method within the arbitrator to be used for putting data.
        joiner: The name of a function or method within the arbitrator to be used for joining.
        joiner_async: The name of an asynchronous function or method within the arbitrator to be used for joining.
        *args: Positional arguments.
        **kwargs: Keyword arguments.
    """

    # Attributes #
    use_proxy: bool = True

    arbitrator: ProcessArbitrator | None = None

    getter: str | None = None
    getter_async: str | None = None
    putter: str | None = None
    putter_async: str | None = None
    joiner: str | None = None
    joiner_async: str | None = None

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        arbitrator: ProcessArbitrator | None = None,
        getter: str | None = None,
        getter_async: str | None = None,
        putter: str | None = None,
        putter_async: str | None = None,
        joiner: str | None = None,
        joiner_async: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        # New Attributes #
        if arbitrator is not None:
            self.arbitrator = arbitrator
        if getter is not None:
            self.getter = getter
        if getter_async is not None:
            self.getter_async = getter_async
        if putter is not None:
            self.putter = putter
        if putter_async is not None:
            self.putter_async = putter_async
        if joiner is not None:
            self.joiner = joiner
        if joiner_async is not None:
            self.joiner_async = joiner_async

        # Parent Attributes #
        super().__init__(*args, **kwargs)

    # Reduction/Pickling
    def __getstate__(self) -> None | dict[str, Any] | tuple[dict[str, Any] | None, dict[str, Any]]:
        """Gets the object's state for pickling.

        If the arbitrator is a proxy, then the proxy is returned instead of the arbitrator.

        Returns:
            The state returned will be either of the following types based on the presence of __dict__ and __slots__:
                None: __dict__ nor __slots__ are present.
                dict: __dict__ is present and __slots__ is not present.
                tuple[None, dict]: __dict__ is not present and __slots__ is present.
                tuple[dict, dict]: __dict__ is present and __slots__ is present.
        """
        state = super().__getstate__()
        if self.use_proxy and (arbitrator := getattr(self, "arbitrator", None)) is not None and arbitrator.is_proxy():
            state["arbitrator"] = arbitrator._proxy
        return state

    # Instance Methods #
    # Get
    def get(self, *args: Any, **kwargs: Any) -> Any:
        """Gets an item using the getter function or method of the arbitrator.

        Args:
            *args: Positional arguments for the getter function or method.
            **kwargs: Keyword arguments for the getter function or method.

        Returns:
            The item returned by the getter function or method.
        """
        return getattr(self.arbitrator, self.getter)(*args, **kwargs)

    async def get_async(self, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously gets an item using the getter_async function or method of the arbitrator.

        Args:
            *args: Positional arguments for the getter_async function or method.
            **kwargs: Keyword arguments for the getter_async function or method.

        Returns:
            The item returned by the getter_async function or method.
        """
        return await getattr(self.arbitrator, self.getter_async)(*args, **kwargs)

    # Put
    def put(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        """Puts an item using the putter function or method of the arbitrator.

        Args:
            value: The value to put into this object.
            *args: Positional arguments for the putter function or method.
            **kwargs: Keyword arguments for the putter function or method.

        Returns:
            The result of the putter function or method.
        """
        return getattr(self.arbitrator, self.putter)(value, *args, **kwargs)

    async def put_async(self, value: Any, *args: Any, **kwargs: Any) -> Any:
        """Asynchronously puts an item using the putter_async function or method of the arbitrator.

        Args:
            value: The value to put into this object.
            *args: Positional arguments for the putter_async function or method.
            **kwargs: Keyword arguments for the putter_async function or method.

        Returns:
            The result of the putter_async function or method.
        """
        return await getattr(self.arbitrator, self.putter_async)(value, *args, **kwargs)

    # Join
    def join(self, *args: Any, **kwargs: Any) -> None:
        """Joins using the joiner function or method of the arbitrator.

        Args:
            *args: Positional arguments for the joiner function or method.
            **kwargs: Keyword arguments for the joiner function or method.
        """
        return getattr(self.arbitrator, self.joiner)(*args, **kwargs)

    async def join_async(self, *args: Any, **kwargs: Any) -> None:
        """Asynchronously joins using the joiner_async function or method of the arbitrator.

        Args:
            *args: Positional arguments for the joiner_async function or method.
            **kwargs: Keyword arguments for the joiner_async function or method.
        """
        return await getattr(self.arbitrator, self.joiner_async)(*args, **kwargs)
