from logging import getLogger
from ..client import ClientIf
from ..server import ServerIf

from .parse import parse_file

log = getLogger(__name__)


class Server(ServerIf):
    def __init__(self, addr: str, params: dict = {}):
        super().__init__(addr, params)
        src = self.params.get("source", None)
        if src is not None:
            res = parse_file(src)
            log.debug("parsed %s", res)

    def serve(self, dispatcher):
        pass


class Client(ClientIf):
    def __init__(self, addr: str, params: dict = {}):
        super().__init__(addr, params)
        src = self.params.get("source", None)
        if src is not None:
            res = parse_file(src)
            log.debug("parsed %s", res)

    def call(self, method: str, params=None):
        pass
