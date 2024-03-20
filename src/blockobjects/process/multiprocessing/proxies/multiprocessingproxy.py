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
from multiprocessing import util, process
from multiprocessing.managers import BaseProxy, dispatch, convert_to_error, listener_client
import threading

# Third-Party Packages #

# Local Packages #
from ...context import ProxyInterface


# Definitions #
# Classes #
class MultiprocessingProxy(BaseProxy, ProxyInterface):

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
        return True

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

    def _callmethod(self, methodname, args=(), kwds={}):
        try:
            conn = self._tls.connection
        except AttributeError:
            util.debug('thread %r does not own a connection', threading.current_thread().name)
            self._connect()
            conn = self._tls.connection

        conn.send((self._id, methodname, args, kwds))
        return self._parse_result(conn.recv())


# Functions #
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

    ProxyType = MakeMultiprocessingProxyType('AutoProxy[%s]' % token.typeid, exposed)
    proxy = ProxyType(token, serializer, manager=manager, authkey=authkey,
                      incref=incref, manager_owned=manager_owned)
    proxy._isauto = True
    return proxy

