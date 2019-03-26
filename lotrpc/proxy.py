import time
from logging import getLogger, INFO

log = getLogger(__name__)


class Proxy:
    def __init__(self, server, client):
        self.server = server
        self.client = client

    def serve(self):
        self.server.serve(self.dispatcher)

    def paramfilter(self, method, param):
        return method, param

    def dispatcher(self, method: str, params=None):
        m, p = self.paramfilter(method, params)
        return self.client.call(m, p)


class LoggingProxy(Proxy):
    def __init__(self, server, client):
        super().__init__(server, client)
        log.setLevel(INFO)

    def dispatcher(self, method: str, params=None):
        ts = time.time()
        res = super().dispatcher(method, params)
        log.info("%s %.3f arg=%s, res=%s", method,
                 time.time() - ts, params, res)
        return res
