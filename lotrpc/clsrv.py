import lotrpc
import click
import json
import time
import copy
import asyncio
import inspect
import queue
import threading
from benchmarker import Benchmarker, Skip
from logging import getLogger, basicConfig, DEBUG
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

log = getLogger(__name__)


def setupLog(verbose):
    if verbose:
        basicConfig(level=DEBUG)


class MyDispatcher(lotrpc.SimpleDispatcher):
    """dispatcher example"""
    seq = 1

    def do_sleep(self, params):
        ts = time.time()
        time.sleep(1)
        params.update({"sleep": time.time() - ts, "seq": self.seq})
        self.seq += 1
        return params

    def do_hello_sleep(self, params):
        ts = time.time()
        time.sleep(1)
        res = {"sleep": time.time() - ts, "seq": self.seq}
        self.seq += 1
        return res

    def do_Greeter_SayHello(self, params):
        log.debug("say hello to %s", params)
        return {"message": "hello {}".format(params.get("name", "anonymous"))}

    def do_Greeter_SayHelloAgain(self, params):
        log.debug("say hello-again to %s", params)
        return {"message": "bye {}".format(params.get("name", "anonymous"))}

    def do_Greeter_SayGoodMorning(self, params):
        log.debug("say gm to %s", params)
        return {"message": "good morning {}".format(params.get("name", "anonymous"))}

    def do_hello(self, params):
        return {"result": "OK"}

    def do_hello_world(self, params):
        return {"result": "OK"}

    def __call__(self, method, params):
        log.debug("my dispatch %s %s", method, params)
        try:
            return super().__call__(method, params)
        except Exception as e:
            # method not found
            log.debug("not found? %s", e)
            return {"rst": "method={}, params={}".format(method, params)}


def do_call_pool(pool, cl, num, method, params):
    ft = []
    for i in range(num):
        ft.append(pool.submit(cl.call, method, copy.deepcopy(params)))
    res = [x.result() for x in ft]
    return "\n".join(map(str, res))


def do_call(cl, num, method, params):
    log.debug("call%d %s %s", num, method, params)
    res = []
    for i in range(num):
        res.append(cl.call(method, params))
    return "\n".join(map(str, res))


def do_call_async(cl, num, method, params):
    res = []
    loop = asyncio.get_event_loop()
    for i in range(num):
        res.append(cl.asynccall(loop, method, copy.deepcopy(params)))
    res = [loop.run_until_complete(x) for x in res]
    return "\n".join(map(str, res))


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())


@cli.command(help="list rpc mode")
def listmode():
    for x in filter(lambda f: inspect.ismodule(getattr(lotrpc, f)), dir(lotrpc)):
        mod = getattr(lotrpc, x)
        if mod.__package__.startswith(lotrpc.__name__):
            if hasattr(mod, "Server"):
                print(x)


@cli.command(help="start server")
@click.option("--options", default="{}")
@click.argument('mode', default='json')
@click.argument('addr', default="http://0.0.0.0:9999/")
@click.option("--verbose/--no-verbose", default=False)
def server(mode, addr, verbose=False, options={}):
    setupLog(verbose)
    mod = getattr(lotrpc, mode)
    srv = mod.Server(addr, json.loads(options))
    srv.serve(MyDispatcher())


@cli.command(help="serialized client")
@click.argument('mode', default='json')
@click.argument('addr', default="http://localhost:9999/")
@click.option("--options", default="{}")
@click.option("--num", type=int, default=1)
@click.option("--method", default="hello", type=str)
@click.option("--params", default='{"p1":true,"p2":[1,2,3]}')
@click.option("--verbose/--no-verbose", default=False)
def client(mode, addr, method, num, params, options, verbose):
    setupLog(verbose)
    mod = getattr(lotrpc, mode)
    cl = mod.Client(addr, json.loads(options))
    res = do_call(cl, num, method, json.loads(params))
    print(res)


@cli.command(help="client with thread pool")
@click.argument('mode', default='json')
@click.argument('addr', default="http://localhost:9999/")
@click.option("--options", default="{}")
@click.option("--num", type=int, default=1)
@click.option("--method", default="hello", type=str)
@click.option("--params", default='{"p1":true,"p2":[1,2,3]}')
@click.option("--verbose/--no-verbose", default=False)
def client_pool(mode, addr, method, num, params, options, verbose):
    setupLog(verbose)
    mod = getattr(lotrpc, mode)
    cl = mod.Client(addr, json.loads(options))
    with ThreadPoolExecutor() as pool:
        res = do_call_pool(pool, cl, num, method, json.loads(params))
    print(res)


@cli.command(help="client with process pool")
@click.argument('mode', default='json')
@click.argument('addr', default="http://localhost:9999/")
@click.option("--options", default="{}")
@click.option("--num", type=int, default=1)
@click.option("--method", default="hello", type=str)
@click.option("--params", default='{"p1":true,"p2":[1,2,3]}')
@click.option("--verbose/--no-verbose", default=False)
def client_ppool(mode, addr, method, num, params, options, verbose):
    setupLog(verbose)
    mod = getattr(lotrpc, mode)
    cl = mod.Client(addr, json.loads(options))
    with ProcessPoolExecutor() as pool:
        res = do_call_pool(pool, cl, num, method, json.loads(params))
    print(res)


@cli.command(help="client with asyncio")
@click.argument('mode', default='json')
@click.argument('addr', default="http://localhost:9999/")
@click.option("--options", default="{}")
@click.option("--num", type=int, default=1)
@click.option("--method", default="hello", type=str)
@click.option("--params", default='{"p1":true,"p2":[1,2,3]}')
@click.option("--verbose/--no-verbose", default=False)
def client_async(mode, addr, method, num, params, options, verbose):
    setupLog(verbose)
    mod = getattr(lotrpc, mode)
    cl = mod.Client(addr, json.loads(options))
    res = do_call_async(cl, num, method, json.loads(params))
    print(res)


@cli.command("proxy", help="start proxy server")
@click.argument('server', default='json')
@click.argument('addr_s', default="http://localhost:9999/")
@click.argument('client', default='msgpack')
@click.argument('addr_c', default="http://localhost:9998/")
@click.option("--client-options", default="{}")
@click.option("--server-options", default="{}")
@click.option("--accesslog/--no-accesslog", default=False)
@click.option("--verbose/--no-verbose", default=False)
def prox(server, addr_s, client, addr_c, client_options, server_options, verbose, accesslog):
    setupLog(verbose)
    srv = getattr(lotrpc, server).Server(addr_s, json.loads(server_options))
    cl = getattr(lotrpc, client).Client(addr_c, json.loads(client_options))
    if accesslog:
        prox = lotrpc.LoggingProxy(srv, cl)
    else:
        prox = lotrpc.Proxy(srv, cl)
    prox.serve()


@cli.command(help="start proxy with authentication example")
@click.argument('server', default='json')
@click.argument('addr_s', default="http://localhost:9999/")
@click.argument('client', default='msgpack')
@click.argument('addr_c', default="http://localhost:9998/")
@click.option("--client-options", default="{}")
@click.option("--server-options", default="{}")
@click.option("--verbose/--no-verbose", default=False)
def proxy_auth(server, addr_s, client, addr_c, client_options, server_options, verbose):
    from lotrpc.proxyauth import LoginProxy
    setupLog(verbose)
    srv = getattr(lotrpc, server).Server(addr_s, json.loads(server_options))
    cl = getattr(lotrpc, client).Client(addr_c, json.loads(client_options))
    prox = LoginProxy(srv, cl)
    prox.serve()


def qworker(q):
    while True:
        item = q.get()
        if item is None:
            break
        item.result()
        q.task_done()


def qworker2(q, loop):
    while True:
        item = q.get()
        if item is None:
            break
        loop.run_until_complete(item)
        q.task_done()


@cli.command(help="start benchmark client")
@click.argument('mode', default='json')
@click.argument('addr', default="http://localhost:9999/")
@click.option("--options", default="{}")
@click.option("--loop", type=int, default=10000)
@click.option("--qsize", type=int, default=100)
@click.option("--method", default="hello", type=str)
@click.option("--params", default='{}')
@click.option("--filter", default=None)
@click.option("--verbose/--no-verbose", default=False)
def benchmark(mode, addr, method, loop, params, options, verbose, qsize, filter):
    setupLog(verbose)
    mod = getattr(lotrpc, mode)
    cl = mod.Client(addr, json.loads(options))
    arg = json.loads(params)
    q = queue.Queue(qsize)

    with Benchmarker(loop, filter=filter) as bench:
        @bench('sync')
        def callapi(bm):
            try:
                for i in bm:
                    cl.call(method, arg)
            except Exception as e:
                raise Skip("error {}".format(e))

        @bench('thread-pool')
        def tpcall(bm):
            try:
                t = threading.Thread(target=qworker, args=(q,))
                t.start()
                with ThreadPoolExecutor() as pool:
                    for i in bm:
                        q.put(pool.submit(cl.call, method, arg))
                    q.put(None)
                t.join()
            except Exception as e:
                raise Skip("error {}".format(e))

        @bench('process-pool')
        def ppcall(bm):
            try:
                t = threading.Thread(target=qworker, args=(q,))
                t.start()
                with ProcessPoolExecutor() as pool:
                    for i in bm:
                        q.put(pool.submit(cl.call, method, arg))
                    q.put(None)
                t.join()
            except Exception as e:
                raise Skip("error {}".format(e))

        @bench('async')
        def asynccall(bm):
            try:
                loop = asyncio.get_event_loop()
                t = threading.Thread(target=qworker2, args=(q, loop))
                t.start()
                for i in bm:
                    q.put(cl.asynccall(loop, method, arg))
                q.put(None)
                t.join()
            except Exception as e:
                raise Skip("error {}".format(e))


if __name__ == '__main__':
    cli()
