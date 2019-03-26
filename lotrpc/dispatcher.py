from logging import getLogger

log = getLogger(__name__)


class SimpleDispatcher:
    prefix = "do_"

    def __call__(self, method, params):
        log.debug("dispatch %s %s", method, params)
        mtn = self.prefix + method.replace(".", "_")
        if hasattr(self, mtn) and callable(getattr(self, mtn)):
            log.debug("found method %s", mtn)
            return getattr(self, mtn)(params)
        log.warning("method not found: %s", mtn)
        raise Exception("method not found: {}".format(mtn))
