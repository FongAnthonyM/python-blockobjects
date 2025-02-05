""" pipefuture.py.py

"""
# Package Header #
from .....header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__

# Imports #
# Standard Libraries #
from asyncio import get_event_loop, Event, InvalidStateError, AbstractEventLoop, sleep
from multiprocessing import Pipe
from multiprocessing.connection import Connection
from typing import Any

# Third-Party Packages #
from baseobjects import BaseObject

# Local Packages #


# Definitions #
# Classes #
class PipeFuture(BaseObject):
    # Attributes #
    _sentinel: object = object()
    loop: AbstractEventLoop = get_event_loop()

    _recv: Event
    _sent: bool = False

    recv_con: Connection | None = None
    send_con: Connection | None = None

    _result: Any = _sentinel

    # Magic Methods #
    # Construction/Destruction
    def __init__(
        self,
        recv_con: Connection | None = None,
        send_con: Connection | None = None,
        *,
        duplex: bool = False,
        loop: AbstractEventLoop | None = None,
        init: bool = True,
    ) -> None:
        # Attributes #
        self._recv = Event()

        # Parent Attributes #
        super().__init__(init=False)

        # Object Construction #
        if init:
            self.construct(recv_con=recv_con, send_con=send_con, duplex=duplex, loop=loop)

    # Picking
    def __getstate__(self) -> dict[str, Any]:
        """Creates a dictionary of attributes which can be used to rebuild this object

        Returns:
            A dictionary of this object's attributes.
        """
        state = self.__dict__.copy()
        del state["loop"]
        return state

    # Coroutine
    def __await__(self, *args, **kwargs):
        """Returns an iterator to be used in await expression. """
        return self.wait_async().__await__()

    # Instance Methods #
    # Constructors/Destructors
    def construct(
        self,
        recv_con: Connection | None = None,
        send_con: Connection | None = None,
        duplex: bool = False,
        *,
        loop: AbstractEventLoop | None = None,
    ) -> None:
        if recv_con is None and send_con is None:
            self.create_pipe(duplex=duplex)

        if loop is not None:
            self.loop = loop

        super().construct()

    def create_pipe(self, duplex: bool = False) -> tuple[Connection, Connection]:
        self.recv_con, self.send_con = connections = Pipe(duplex=duplex)
        return connections

    def close(self) -> None:
        self.recv_con.close()
        self.send_con.close()
        self.recv_con = None
        self.send_con = None

    def get_loop(self, *args, **kwargs) -> AbstractEventLoop:
        """ Return the event loop the Future is bound to. """
        return self.loop

    def done(self) -> bool:
        return self._result is not self._sentinel

    def set_result(self, result, *args, **kwargs) -> None:
        """

        Args:
            result:
            *args:
            **kwargs:
        """
        if self._sent:
            raise InvalidStateError
        else:
            self.send_con.send(result)
            self._sent = True

    def parse_result(self, result) -> Any:
        return result

    def wait(self) -> None:
        if self._result is self._sentinel:
            self._result = self.recv_con.recv()

        return self.parse_result(self._result)

    # async def _wait_async(self) -> None:
    #     fd = self.recv_con.fileno()
    #     self.loop.add_reader(fd, self._recv.set)
    #
    #     while not self.recv_con.poll():
    #         await self._recv.wait()
    #         self._recv.clear()
    #
    #     self.loop.remove_reader(fd)
    #     self._result = self.recv_con.recv()

    async def _wait_async(self) -> None:
        while not self.recv_con.poll():
            await sleep(0)

        self._result = self.recv_con.recv()

    async def wait_async(self) -> Any:
        if self._result is self._sentinel:
            await self._wait_async()

        return self.parse_result(self._result)

    def result(self, *args, **kwargs) -> Any:
        """Returns the result this future represents.

        If the future has been cancelled, raises CancelledError.  If the
        future's result isn't yet available, raises InvalidStateError.  If
        the future is done and has an exception set, this exception is raised.
        """
        return self.wait()




