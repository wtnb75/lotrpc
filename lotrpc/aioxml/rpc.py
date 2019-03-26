import asyncio
import functools
from aiohttp_xmlrpc.handler import XMLRPCView
from aiohttp_xmlrpc.client import ServerProxy
from aiohttp import web

from ..client import ClientIf
from ..server import ServerIf


class Server(ServerIf):
    class MyHandler(XMLRPCView):
        def _lookup_method(self, method_name):
            res = functools.partial(self.d, method_name)
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
        res = self.cl[method](params)
        return self.loop.run_until_complete(res)

    def __del__(self):
        return self.loop.run_until_complete(self.cl.close())
