""" multiprocessingproxy.py

"""
# Package Header #
from ....header import *

# Header #
__author__ = __author__
__credits__ = __credits__
__maintainer__ = __maintainer__
__email__ = __email__


# Imports #
# Standard Libraries #
from collections.abc import Iterable, Generator
from functools import partialmethod
import multiprocessing
from multiprocessing import util, process
from multiprocessing.connection import address_type, Connection
from multiprocessing.managers import (BaseProxy, dispatch, RemoteError,
                                      convert_to_error, listener_client, get_spawning_popen, State)
import os
import socket
import threading
from typing import Any, ClassVar

# Third-Party Packages #
from baseobjects.typing import AnyCallable
from baseobjects.operations import iter_public_method_names

# Local Packages #
from ...context import ProxyInterface
try:
    import numpy
except ModuleNotFoundError:
    NUMPY_EXISTS = False
else:
    NUMPY_EXISTS = True
    from ...sharedmemory.sharedarray import DEFAULT_ARRAY_REDUCER


# Definitions #
# Classes #
class MultiprocessingProxy(BaseProxy, ProxyInterface):

    # Static Methods #
    @staticmethod
    def _call_inner_method(obj, name, *args, **kwargs):
        """Evaluates the wrapped object's method."""
        return obj._callmethod(name, args, kwargs)

    # Class Attributes #
    _proxy_classes: ClassVar[dict[type, dict[tuple[str, tuple], type]]] = {}
    _exposed_: ClassVar[set] = set()
    _unexposed_: ClassVar[set] = set()
    exposed: ClassVar[set]
    __exposed__: ClassVar[set]

    # Class Methods #
    @classmethod
    def get_exposed(cls, target_cls: type, exposed: Iterable[str] | None = None) -> set[str]:
        public_methods = set(iter_public_method_names(target_cls))
        exposed = set(exposed or ())
        c_exposed = set(getattr(target_cls, "exposed", ())) | set(getattr(target_cls, "_exposed_", ()))
        c_unexposed = set(getattr(target_cls, "unexposed", ())) | set(getattr(target_cls, "_unexposed_", ()))
        p_exposed = cls._exposed_
        p_unexposed = cls._unexposed_
        return (public_methods | exposed | c_exposed | p_exposed) - c_unexposed - p_unexposed

    @classmethod
    def _create_proxy_method(cls, name: str) -> AnyCallable:
        """A factory for creating method functions for accessing a proxy's methods.

        Args:
            name: The name of the method

        Returns:
            The function for a method.
        """
        return partialmethod(cls._call_inner_method, name)

    @classmethod
    def create_proxy_type(cls, name: str, exposed: Iterable[str]) -> type:
        # Create Storage Key
        exposed = tuple(exposed)
        key = (name, exposed)

        # Get Class Register
        if (proxy_classes := cls._proxy_classes.get(cls, None)) is None:
            cls._proxy_classes[cls] = proxy_classes = {}

        # Create and Register Class if it does not exist
        if (proxy_class := proxy_classes.get(key, None)) is None:
            dic = {}
            for name in exposed:
                exec('''def %s(self, /, *args, **kwds):
                        return self._callmethod(%r, args, kwds)''' % (name, name), dic)
            proxy_classes[key] = proxy_class = type(name, (cls,), dic)
            proxy_class.__exposed__ = set(exposed)

        # Return Proxy Class
        return proxy_class

    @classmethod
    def new_proxy(
        cls,
        target_cls: type,
        args=(),
        kwargs=None,
        *_args,
        exposed: Iterable[str] | None = None,
        **_kwargs,
    ) -> "MultiprocessingProxy":
        # Create Proxy Type
        name = f"AutoMultiprocessingProxy{target_cls.__name__}"
        exposed = cls.get_exposed(target_cls=target_cls, exposed=exposed)
        proxy_type = cls.create_proxy_type(name=name, exposed=exposed)

        # Return Proxy
        return proxy_type(cls=target_cls, args=args, kwargs=kwargs, exposed=exposed, **_kwargs)

    def __reduce__(self):
        kwds = {}
        if get_spawning_popen() is not None:
            kwds['authkey'] = self._authkey

        if getattr(self, '_isauto', False):
            kwds['exposed'] = self.__exposed__ or self._exposed_
            return (RebuildProxy, (AutoMultiprocessingProxy, self._token, self._serializer, kwds))
        else:
            return (RebuildProxy, (type(self), self._token, self._serializer, kwds))

    def _create_proxy(self, token, exposed):
        proxytype = self._manager._registry[token.typeid][-1]
        token.address = self._token.address
        proxy = proxytype(
            token, self._serializer, manager=self._manager,
            authkey=self._authkey, exposed=exposed
        )
        conn = self._Client(token.address, authkey=self._authkey)
        dispatch(conn, None, 'decref', (token.id,))
        return proxy

    # State
    def _is_alive(self) -> bool:
        """Returns True if the proxy server is alive, False otherwise."""
        return True

    # Server
    def _parse_result(self, result):
        kind, item = result
        match kind:
            case '#RETURN':
                return item
            case '#PROXY':
                exposed, token = item
                return self._create_proxy(token, exposed)
            case '#FUTURE':
                item.parse_result = self._parse_result
                return item

        raise convert_to_error(kind, item)

    if NUMPY_EXISTS:
        def _callmethod(self, methodname, args=(), kwds={}):
            try:
                conn = self._tls.connection
            except AttributeError:
                util.debug('thread %r does not own a connection', threading.current_thread().name)
                self._connect()
                conn = self._tls.connection

            with DEFAULT_ARRAY_REDUCER.persist():
                conn.send((self._id, methodname, args, kwds))
                return self._parse_result(conn.recv())

    else:
        def _callmethod(self, methodname, args=(), kwds={}):
            try:
                conn = self._tls.connection
            except AttributeError:
                util.debug('thread %r does not own a connection', threading.current_thread().name)
                self._connect()
                conn = self._tls.connection

            conn.send((self._id, methodname, args, kwds))
            return self._parse_result(conn.recv())

    def _delref(self, auto_shutdown: bool = True) -> None:
        # check whether manager is still alive
        try:
            util.debug('DELREF %r', self._token.id)
            conn = self._Client(self._token.address, authkey=self._authkey)
            dispatch(conn, None, 'delref', (self._token.id,))
        except Exception as e:
            util.debug('DELREF %r -- proxy already shutdown', self._token.id)

        if auto_shutdown and self._manager is not None and self._manager._number_of_objects() == 0:
            self._manager.shutdown()

        # check whether we can close this thread's connection because
        # the process owns no more references to objects for this manager
        if not self._idset and hasattr(self._tls, 'connection'):
            util.debug('thread %r has no more proxies so closing conn', threading.current_thread().name)
            self._tls.connection.close()
            del self._tls.connection

    def _kill_server(self) -> None:
        """Kills the server which the proxy is running on."""
        self._delref()


# Functions #
def SocketClient(address):
    """Establishes a socket connection to the given address.

    This function is intend to override python's implementation of SocketClient, because the original implementation
    does not handle race conditions.

    When a race condition occurs the connection is refused. This implementation will keep trying to connect until a
    stable connection is established. Once connected, it detaches the socket and returns a Connection object.

    Args:
        address: The address to connect to. The address type is determined by the address_type function.

    Returns:
        Connection: A multiprocessing Connection object that represents the socket connection.

    Raises:
        ConnectionRefusedError: The function will catch this exception and keep trying to connect.
    """
    family = address_type(address)
    with socket.socket(getattr(socket, family)) as s:
        s.setblocking(True)
        while True:
            try:
                s.connect(address)
                return Connection(s.detach())
            except ConnectionRefusedError:
                pass


def RebuildProxy(func, token, serializer, kwds):
    server = getattr(process.current_process(), '_manager_server', None)
    if server and server.address == token.address:
        util.debug('Rebuild a proxy owned by manager, token=%r', token)
        kwds['manager_owned'] = True
        if token.id not in server.id_to_local_proxy_obj:
            server.id_to_local_proxy_obj[token.id] = server.id_to_obj[token.id]
    incref = kwds.pop('incref', True) and not getattr(process.current_process(), '_inheriting', False)
    try:
        return func(token, serializer, incref=incref, **kwds)
    except RemoteError as e:
        return None


def MakeMultiprocessingProxyType(name, exposed, _cache={}) -> type:
    exposed = tuple(exposed)
    try:
        return _cache[(name, exposed)]
    except KeyError:
        pass

    dic = {}

    for meth in exposed:
        exec('''def %s(self, /, *args, **kwds):
        return self._callmethod(%r, args, kwds)''' % (meth, meth), dic)

    ProxyType = type(name, (MultiprocessingProxy,), dic)
    ProxyType._exposed_ = exposed
    _cache[(name, exposed)] = ProxyType
    return ProxyType


def AutoMultiprocessingProxy(token, serializer, manager=None, authkey=None, exposed=None, incref=True, manager_owned=False):
    _Client = listener_client[serializer][1]

    if exposed is None:
        conn = _Client(token.address, authkey=authkey)
        try:
            exposed = dispatch(conn, None, 'get_methods', (token,))
        finally:
            conn.close()

    if authkey is None and manager is not None:
        authkey = manager._authkey
    if authkey is None:
        authkey = process.current_process().authkey

    # ProxyType = MakeMultiprocessingProxyType('AutoProxy[%s]' % token.typeid, exposed)
    # proxy = ProxyType(token, serializer, manager=manager, authkey=authkey, incref=incref, manager_owned=manager_owned)
    name = f"AutoMultiprocessingProxy{token.typeid}"
    ProxyType = MultiprocessingProxy.create_proxy_type(name, exposed=exposed)
    proxy = ProxyType(token, serializer, manager=manager, authkey=authkey, incref=incref, manager_owned=manager_owned)
    proxy._isauto = True
    return proxy


# Overrides #
multiprocessing.connection.SocketClient = SocketClient

