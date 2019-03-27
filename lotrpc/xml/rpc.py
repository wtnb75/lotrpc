# XML-RPC Server/Client
from ..server import ServerIf
from ..client import ClientIf
import threading
import xmlrpc.server
import xmlrpc.client
from logging import getLogger

log = getLogger(__name__)


class Server(ServerIf):
    class XServ:
        def initialize(self, d):
            self.d = d

        def _dispatch(self, method, params):
            log.debug("got %s %s", method, params)
            return self.d(method, *params)

    def serve(self, d):
        xs = self.XServ()
        xs.initialize(d)
        hdl = type("XHandler", (xmlrpc.server.SimpleXMLRPCRequestHandler,), {
                   "rpc_paths": (self.params.get("baseurl", self.addr_parsed.path),)})
        srv = xmlrpc.server.SimpleXMLRPCServer(
            (self.addr_parsed.hostname, self.addr_parsed.port), requestHandler=hdl, logRequests=False)
        srv.register_instance(xs)
        srv.serve_forever()


class Client(ClientIf):
    def __init__(self, addr: str, params: dict = {}):
        super().__init__(addr, params)
        self.tl = threading.local()

    def call(self, method: str, params=None):
        log.debug("call %s %s", method, params)
        # cl = xmlrpc.client.ServerProxy(self.addr)
        if not hasattr(self.tl, "sp"):
            log.debug("create proxy")
            self.tl.sp = xmlrpc.client.ServerProxy(self.addr)
        fn = self.tl.sp
        for k in method.split("."):
            fn = getattr(fn, k)
        return fn(params)
