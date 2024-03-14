""" multiprocessingproxyserver.py

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
from multiprocessing import util
from multiprocessing.managers import SharedMemoryManager, dispatch

# Third-Party Packages #

# Local Packages #
from .multiprocessingproxy import AutoMultiprocessingProxy


# Definitions #
# Classes #
class MultiprocessingProxyServer(SharedMemoryManager):
    @classmethod
    def register(cls, typeid, callable=None, proxytype=None, exposed=None, method_to_typeid=None, create_method=True):
        if '_registry' not in cls.__dict__:
            cls._registry = cls._registry.copy()

        if proxytype is None:
            proxytype = AutoMultiprocessingProxy

        exposed = exposed or getattr(proxytype, '_exposed_', None)

        method_to_typeid = method_to_typeid or \
                           getattr(proxytype, '_method_to_typeid_', None)

        if method_to_typeid:
            for key, value in list(method_to_typeid.items()):  # isinstance?
                assert type(key) is str, '%r is not a string' % key
                assert type(value) is str, '%r is not a string' % value

        cls._registry[typeid] = (
            callable, exposed, method_to_typeid, proxytype
        )

        if create_method:
            def temp(self, /, *args, **kwds):
                util.debug('requesting creation of a shared %r object', typeid)
                token, exp = self._create(typeid, *args, **kwds)
                proxy = proxytype(
                    token, self._serializer, manager=self,
                    authkey=self._authkey, exposed=exp
                )
                conn = self._Client(token.address, authkey=self._authkey)
                dispatch(conn, None, 'decref', (token.id,))
                return proxy

            temp.__name__ = typeid
            setattr(cls, typeid, temp)
