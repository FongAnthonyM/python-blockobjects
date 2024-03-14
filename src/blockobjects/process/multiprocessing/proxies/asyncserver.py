""" asyncserver.py

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
from multiprocessing import util
from multiprocessing.managers import SharedMemoryServer, Token
import sys
import threading
from traceback import format_exc

# Third-Party Packages #

# Local Packages #
from ..futures import PipeFuture


# Definitions #
# Classes #
class AsyncServer(SharedMemoryServer):

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
                    if iscoroutine(function):
                        # Run Coroutine in Thread
                        t_future = run_coroutine_threadsafe(res, self._loop)
                        # Check if coroutine is done, returning the result otherwise, return a future.
                        if t_future.done():
                            res = t_future.result()
                        else:
                            c_future = PipeFuture()
                            t = threading.Thread(target=self.set_future_result, args=(c_future, t_future, conn, typeid))
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
