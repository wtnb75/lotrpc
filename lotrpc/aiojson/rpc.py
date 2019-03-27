import asyncio
import functools
from aiohttp_jsonrpc.handler import JSONRPCView
from aiohttp_jsonrpc.client import ServerProxy
from aiohttp import web

from ..client import ClientIf
from ..server import ServerIf


class Server(ServerIf):
    class MyHandler(JSONRPCView):
        def _d1(self, method, **params):
            return self.d(method, params)

        def _lookup_method(self, method_name):
            res = functools.partial(self._d1, method_name)
            res.__module__ = ""
            res.__name__ = method_name
            return res

    def serve(self, dispatcher):
        hdl = type("CustomHandler", (self.MyHandler,), {"d": dispatcher})
        app = web.Application()
        app.router.add_route('*', self.addr_parsed.path, hdl)
        web.run_app(app, host=self.addr_parsed.hostname,
                    port=self.addr_parsed.port)


class Client(ClientIf):
    def __init__(self, addr: str, params: dict = {}):
        super().__init__(addr, params)
        self.cl = ServerProxy(self.addr)
        self.loop = asyncio.get_event_loop()

    def call(self, method: str, params=None):
        if isinstance(params, dict):
            res = self.cl[method](**params)
        elif isinstance(params, (tuple, list)):
            res = self.cl[method](*params)
        else:
            res = self.cl[method](params)
        return self.loop.run_until_complete(res)

    def __del__(self):
        return self.loop.run_until_complete(self.cl.close())
