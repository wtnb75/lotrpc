# MessagePack-RPC Server/Client
from ..server import ServerIf
from ..client import ClientIf
import msgpackrpc
import functools
import threading
from logging import getLogger
from concurrent.futures import ThreadPoolExecutor

log = getLogger(__name__)


def conv(s, encoding='utf-8'):
    if isinstance(s, dict):
        res = {}
        for k, v in s.items():
            if isinstance(k, bytes):
                res[k.decode(encoding)] = conv(v, encoding)
            else:
                res[k] = conv(v, encoding)
        return res
    if isinstance(s, bytes):
        return s.decode(encoding)
    if isinstance(s, (list, tuple)):
        return [conv(x, encoding) for x in s]
    return s


class Server(ServerIf):
    class MPServ(msgpackrpc.Server):
        executor = ThreadPoolExecutor()

        def __init__(self, dispatcher):
            super().__init__(dispatcher, pack_encoding='utf-8', unpack_encoding='utf-8')

        def initialize(self, d):
            self.d = d

        def done_async(self, responder, result):
            responder.set_result(result.result(), None)

        def dispatch(self, method, param, responder):
            log.debug("got %s %s %s", method, param, responder)
            method = msgpackrpc.compat.force_str(method)
            ft = Server.MPServ.executor.submit(self.d, method, *param)
            ft.add_done_callback(functools.partial(
                self.done_async, responder))

    def serve(self, dispatcher):
        mpsrv = Server.MPServ(None)
        mpsrv.initialize(dispatcher)
        # srv = msgpackrpc.Server(mpsrv)
        mpsrv.listen(msgpackrpc.Address(
            self.addr_parsed.hostname, self.addr_parsed.port))
        try:
            mpsrv.start()
        except KeyboardInterrupt:
            log.info("stop")
            mpsrv.stop()


class Client(ClientIf):
    def __init__(self, addr: str, params: dict = {}):
        super().__init__(addr, params)
        self.tl = threading.local()

    def call(self, method: str, params=None):
        log.debug("call %s %s", method, params)
        if not hasattr(self.tl, "cl"):
            self.tl.cl = msgpackrpc.Client(msgpackrpc.Address(
                self.addr_parsed.hostname, self.addr_parsed.port),
                pack_encoding='utf-8', unpack_encoding='utf-8')
        return self.tl.cl.call(method, params)
