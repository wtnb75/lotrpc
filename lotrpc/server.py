import urllib.parse


class ServerIf:
    def __init__(self, addr: str, params: dict = {}):
        self.addr = addr      # URL or host:port
        self.params = params  # options
        try:
            if addr.find("/") == -1:
                addr = "//" + addr
            self.addr_parsed = urllib.parse.urlsplit(addr)
        except Exception:
            pass

    def serve(self, dispatcher):
        pass
