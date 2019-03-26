import urllib.parse


class ClientIf:

    def __init__(self, addr: str, params: dict = {}):
        self.addr = addr       # URL or host:port
        self.params = params   # Client options
        try:
            if addr.find("/") == -1:
                addr = "//" + addr
            self.addr_parsed = urllib.parse.urlsplit(addr)
        except Exception:
            pass

    def call(self, method: str, params=None):
        pass

    def asynccall(self, loop, method: str, params=None):
        return loop.run_in_executor(None, self.call, method, params)
