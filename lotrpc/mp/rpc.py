# MessagePack-RPC Server/Client with mprpc module
from ..client import ClientIf
from ..server import ServerIf
from logging import getLogger
import functools

import mprpc
import mprpc.exceptions
from gevent.server import StreamServer

log = getLogger(__name__)


class Server(ServerIf):
    class MPServ(mprpc.RPCServer):
        def __getattr__(self, name, dflt=None):
            log.debug("getattr %s", name)
            return functools.partial(self.d, name)
            # try:
            #    if hasattr(self, name):
            #        return getattr(self, name, dflt)
            # finally:
            #    return functools.partial(self.d, self, name)

    def serve(self, dispatcher):
        # does not work
        srv = Server.MPServ()
        srv.d = dispatcher
        server = StreamServer(
            (self.addr_parsed.hostname, self.addr_parsed.port), srv)
        server.serve_forever()


class Client(ClientIf):
    def call(self, method: str, params=None):
        log.debug("connect host=%s port=%s",
                  self.addr_parsed.hostname, self.addr_parsed.port)
        cl = mprpc.RPCClient(self.addr_parsed.hostname, self.addr_parsed.port)
        log.debug("call %s(%s)", method, params)
        return cl.call(method, params)
