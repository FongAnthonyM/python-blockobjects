""" multiprocessingproxyserver.py

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
import multiprocessing
from multiprocessing import util, ProcessError, connection
from multiprocessing.managers import SharedMemoryManager, Token, dispatch, State, convert_to_error
import signal
from traceback import format_exc

# Third-Party Packages #

# Local Packages #
from .multiprocessingasyncserver import MultiprocessingAsyncServer
from .multiprocessingproxy import AutoMultiprocessingProxy


# Definitions #
# Classes #
class MultiprocessingProxyServer(SharedMemoryManager):
    _Server = MultiprocessingAsyncServer

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

    @classmethod
    def _run_server_proxy(
        cls,
        registry,
        address,
        authkey,
        serializer,
        writer,
        initializer=None,
        initargs=(),
        proxy_name=None,
        proxy_args=(),
        proxy_kwargs=None,
    ):
        """Create a server, report its address and run it"""
        # bpo-36368: protect server process from KeyboardInterrupt signals
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        if initializer is not None:
            initializer(*initargs)

        # create server
        server = cls._Server(registry, address, authkey, serializer)

        # inform parent process of the server's address
        writer.send(server.address)

        # Create Proxy
        try:
            result = server.create(None, proxy_name, *proxy_args, **proxy_kwargs)
        except Exception:
            msg = ('#TRACEBACK', format_exc())
        else:
            msg = ('#RETURN', result)
        writer.send(msg)

        writer.close()

        # run the manager
        util.info('manager serving at %r', server.address)
        server.serve_forever()

    def __del__(self):
        super().__del__()
        try:
            self.shutdown()
        except:
            pass

    def is_alive(self):
        return self._state.value == State.STARTED

    def start_proxy(self, initializer=None, initargs=(), proxy_name=None, proxy_args=(), proxy_kwargs=None):
        '''
        Spawn a server process for this manager object
        '''
        if self._state.value != State.INITIAL:
            if self._state.value == State.STARTED:
                raise ProcessError("Already started server")
            elif self._state.value == State.SHUTDOWN:
                raise ProcessError("Manager has shut down")
            else:
                raise ProcessError(
                    "Unknown state {!r}".format(self._state.value))

        if initializer is not None and not callable(initializer):
            raise TypeError('initializer must be a callable')

        # pipe over which we will retrieve address of server
        reader, writer = connection.Pipe(duplex=False)

        # spawn process which runs a server
        self._process = self._ctx.Process(
            target=type(self)._run_server_proxy,
            args=(
                self._registry,
                self._address,
                self._authkey,
                self._serializer,
                writer,
                initializer,
                initargs,
                proxy_name,
                proxy_args,
                proxy_kwargs,
            ),
        )
        ident = ':'.join(str(i) for i in self._process._identity)
        self._process.name = type(self).__name__ + '-' + ident
        self._process.start()
        writer.close()

        # get address of server
        self._address = reader.recv()

        # get the proxy info
        kind, result = reader.recv()
        if kind != '#RETURN':
            raise convert_to_error(kind, result)

        reader.close()

        # register a finalizer
        self._state.value = State.STARTED
        self.shutdown = util.Finalize(
            self, type(self)._finalize_manager,
            args=(self._process, self._address, self._authkey, self._state,
                  self._Client, self._shutdown_timeout),
            exitpriority=0
            )

        # Build the proxy
        id, exp = result
        token = Token(proxy_name, self._address, id)
        proxy = self._registry[proxy_name][3](
            token,
            self._serializer,
            manager=self,
            authkey=self._authkey,
            exposed=exp,
        )
        conn = self._Client(token.address, authkey=self._authkey)
        dispatch(conn, None, 'decref', (token.id,))
        return proxy
