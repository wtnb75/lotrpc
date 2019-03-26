# JSON-RPC Server/Client
from ..server import ServerIf
from ..client import ClientIf
import json
import requests
from logging import getLogger
import tornado.web
from tornado.gen import coroutine as tasync
# from tornado.web import asynchronous as tasync
from tornado.ioloop import IOLoop
from concurrent.futures import ThreadPoolExecutor
from tornado.platform.asyncio import to_tornado_future

log = getLogger(__name__)


class Server(ServerIf):
    class Handler(tornado.web.RequestHandler):
        executor = ThreadPoolExecutor()

        def initialize(self, d):
            log.debug("initialize %s", d)
            self.d = d

        def set_default_headers(self):
            self.set_header("content-type", "application/json")

        async def bgtask(self, method, params):
            ft = Server.Handler.executor.submit(self.d, method, params)
            result = await to_tornado_future(ft)
            return result

        @tasync
        def post(self):
            payload = json.loads(self.request.body)
            log.debug("got request %s", payload)
            method = payload.get("method")
            params = payload.get("params", {})
            result = yield from self.bgtask(method, params)
            resp = {
                "result": result,
                "id": payload.get("id"),
            }
            json.dump(resp, self, ensure_ascii=False)

    def __init__(self, addr: str, params: dict = {}):
        super().__init__(addr, params)
        self.baseurl = self.addr_parsed.path

    def serve(self, fn):
        app = tornado.web.Application(
            handlers=[(self.baseurl, self.Handler, {"d": fn}), ])
        app.listen(self.addr_parsed.port)
        try:
            IOLoop.current().start()
        except RuntimeError as e:
            log.error("error %s", e)
            # raise e


class Client(ClientIf):
    hdrs = {
        "content-type": "application/json",
    }

    def call(self, method, params=None):
        payload = {
            "method": method,
            "params": params,
            "jsonrpc": "2.0",
            "id": 0,
        }
        log.debug("send request %s", payload)
        return requests.post(self.addr, data=json.dumps(payload), headers=self.hdrs).json().get("result")
