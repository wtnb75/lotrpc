import bcrypt
import secrets
import time
from logging import getLogger
from .proxy import Proxy

log = getLogger(__name__)


class LoginProxy(Proxy):
    unauth_method = ["login", "logout"]
    token_key = "auth"
    pwd_store = {
        "testuser": bcrypt.hashpw(b"testpassword", bcrypt.gensalt(rounds=10, prefix=b'2a')),
    }
    token_store = {}
    token_expire = 3600
    token_update = True

    def login(self, params):
        username = params.get("username", None)
        password = params.get("password", None)
        if username is None or password is None:
            return {"error": "invalid username or password"}
        pw = self.pwd_store.get(username, None)
        if pw is None:
            return {"error": "invalid username or password"}
        if not bcrypt.checkpw(password.encode("utf-8"), pw):
            return {"error": "invalid username or password"}
        # generate token
        token = secrets.token_urlsafe()
        self.token_store[token] = (username, time.time())
        return {
            self.token_key: token,
        }

    def logout(self, params):
        token = params.get(self.token_key, None)
        if token in self.token_store:
            self.token_store.pop(token)
        return {}

    def _check_token(self, token):
        if token in self.token_store:
            user, ts = self.token_store[token]
            if ts - time.time() > self.token_expire:
                self.token_store.pop(token)
                return None
            if self.token_update:
                self.token_store[token] = (user, time.time())
            return user
        return None

    def dispatcher(self, method: str, params: dict = {}):
        if method in self.unauth_method:
            return getattr(self, method)(params)
        username = self._check_token(params.get(self.token_key, None))
        if username is not None:
            params.pop(self.token_key)
            params["username"] = username
            return super().dispatcher(method, params)
        return {"error": "not logged in"}
