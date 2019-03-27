# ZeroRPC server/client
from logging import getLogger
import threading
import functools
import zerorpc

from ..client import ClientIf
from ..server import ServerIf

log = getLogger(__name__)


class ZeroServer(zerorpc.Server):
    def __call__(self, method, *args):
        log.debug("call %s, args=%s", method, args)
        try:
            return super().__call__(self, method, *args)
        except NameError:
            log.debug("call dispatch %s", method)
            return self._dispatch(method, args)


class MyDict(dict):
    def __init__(self, d, kv):
        self.d = d
        self.kv = kv

    def do_call(self, method, *params, **kwargs):
        log.debug("calls: %s param=%s, kwargs=%s", method, params, kwargs)
        return self.d(method, *params)

    def __hasattr__(self, k):
        return k in self.kv

    def get(self, k, defval):
        try:
            return self.kv[k]
        except KeyError:
            log.debug("get %s def=%s", k, defval)
            res = functools.partial(self.do_call, k)
            setattr(res, "__name__", k)
            log.debug("return: %s", res)
            return zerorpc.decorators.rep(res)


class Server(ServerIf):
    def serve(self, dispatcher):
        log.debug("start server %s:%s", self.addr_parsed.hostname,
                  self.addr_parsed.port)
        srv = ZeroServer()
        # srv._dispatch = dispatcher
        srv._methods = MyDict(dispatcher, srv._methods)
        srv.bind("tcp://%s:%s" %
                 (self.addr_parsed.hostname, self.addr_parsed.port))
        log.debug("methods: %s", srv._methods)
        srv.run()


class Client(ClientIf):
    def __init__(self, addr: str, params: dict = {}):
        super().__init__(addr, params)
        self.tl = threading.local()

    def call(self, method: str, params=None):
        log.debug("start client %s:%s", self.addr_parsed.hostname,
                  self.addr_parsed.port)
        if not hasattr(self.tl, "cl"):
            log.debug("create client")
            self.tl.cl = zerorpc.Client()
            self.tl.cl.connect("tcp://%s:%s" %
                               (self.addr_parsed.hostname, self.addr_parsed.port))
        return self.tl.cl(method, params)
