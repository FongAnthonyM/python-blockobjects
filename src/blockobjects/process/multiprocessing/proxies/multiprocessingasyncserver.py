""" multiprocessingasyncserver.py

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
from asyncio import AbstractEventLoop, iscoroutine, run_coroutine_threadsafe, get_event_loop
from concurrent.futures import Future
from multiprocessing import util
from multiprocessing.managers import SharedMemoryServer, Token
import sys
import threading
from time import sleep
from traceback import format_exc

# Third-Party Packages #

# Local Packages #
from ..futures import PipeFuture


# Definitions #
# Classes #
class MultiprocessingAsyncServer(SharedMemoryServer):
    public = SharedMemoryServer.public + ['delref']

    def __init__(self, *args, **kwargs):
        SharedMemoryServer.__init__(self, *args, **kwargs)
        self._loop = get_event_loop()
        thread = threading.Thread(target=self.run_event_loop, args=(self._loop,))
        thread.daemon = True
        thread.start()

    def run_event_loop(self, loop: AbstractEventLoop):
        """ Run asyncio event loop """
        loop.run_forever()

    def set_future_result(self, c_future, future, conn, typeid):
        res = future.result()
        if typeid:
            rident, rexposed = self.create(conn, typeid, res)
            token = Token(typeid, self.address, rident)
            msg = ('#PROXY', (rexposed, token))
        else:
            msg = ('#RETURN', res)
        c_future.set_result(msg)

    def serve_client(self, conn):
        util.debug('starting server thread to service %r', threading.current_thread().name)

        recv = conn.recv
        send = conn.send
        id_to_obj = self.id_to_obj

        while not self.stop_event.is_set():

            try:
                # Listen for Method
                methodname = obj = None
                request = recv()
                ident, methodname, args, kwds = request
                try:
                    obj, exposed, gettypeid = id_to_obj[ident]
                except KeyError as ke:
                    try:
                        obj, exposed, gettypeid = self.id_to_local_proxy_obj[ident]
                    except KeyError:
                        raise ke

                if methodname not in exposed:
                    raise AttributeError(f'method {methodname} of {type(obj)} object is not in exposed={exposed}')

                # Execute Method
                msg = ()
                function = getattr(obj, methodname)
                try:
                    res = function(*args, **kwds)
                    typeid = gettypeid and gettypeid.get(methodname, None)
                    if iscoroutine(res):
                        # Run Coroutine in Thread
                        res = run_coroutine_threadsafe(res, self._loop)
                    if isinstance(res, Future):
                        c_future = PipeFuture(loop=self._loop)
                        # Check if coroutine is done, returning the result otherwise, return a future.
                        if res.done():
                            res =  res.result()
                            if typeid:
                                rident, rexposed = self.create(conn, typeid, res)
                                token = Token(typeid, self.address, rident)
                                msg = ('#PROXY', (rexposed, token))
                            else:
                                msg = ('#RETURN', res)
                            c_future._result = msg
                            c_future.close()
                        else:
                            t = threading.Thread(target=self.set_future_result, args=(c_future, res, conn, typeid))
                            t.daemon = True
                            t.start()
                        msg = ('#FUTURE', c_future)
                except Exception as e:
                    msg = ('#ERROR', e)
                else:
                    if typeid:
                        rident, rexposed = self.create(conn, typeid, res)
                        token = Token(typeid, self.address, rident)
                        msg = ('#PROXY', (rexposed, token))
                    elif not msg:
                        msg = ('#RETURN', res)

            except AttributeError:
                if methodname is None:
                    msg = ('#TRACEBACK', format_exc())
                else:
                    try:
                        fallback_func = self.fallback_mapping[methodname]
                        result = fallback_func(self, conn, ident, obj, *args, **kwds)
                        msg = ('#RETURN', result)
                    except Exception:
                        msg = ('#TRACEBACK', format_exc())

            except EOFError:
                util.debug('got EOF -- exiting thread serving %r', threading.current_thread().name)
                sys.exit(0)

            except Exception:
                msg = ('#TRACEBACK', format_exc())

            # Send Message with contents
            try:
                try:
                    send(msg)
                except Exception:
                    send(('#UNSERIALIZABLE', format_exc()))
            except Exception as e:
                util.info('exception in thread serving %r', threading.current_thread().name)
                util.info(' ... message was %r', msg)
                util.info(' ... exception was %r', e)
                conn.close()
                sys.exit(1)

    def delref(self, c, ident):
        if ident not in self.id_to_refcount and ident in self.id_to_local_proxy_obj:
            util.debug('Server DECREF skipping %r', ident)
            return

        with self.mutex:
            self.id_to_refcount[ident] = 0
            del self.id_to_refcount[ident]

        if ident not in self.id_to_refcount:
            # Two-step process in case the object turns out to contain other
            # proxy objects (e.g. a managed list of managed lists).
            # Otherwise, deleting self.id_to_obj[ident] would trigger the
            # deleting of the stored value (another managed object) which would
            # in turn attempt to acquire the mutex that is already held here.
            self.id_to_obj[ident] = (None, (), None)  # thread-safe
            util.debug('disposing of obj with id %r', ident)
            with self.mutex:
                del self.id_to_obj[ident]
