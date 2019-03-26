# lotrpc: RPC abstraction layer

lotrpc unifies a lot of RPC protocols.

protocols:

- XML-RPC http://xmlrpc.scripting.com/
- JSON RPC https://www.jsonrpc.org/specification
- MessagePack RPC https://msgpack.org/
- gRPC https://grpc.io/
- ZeroRPC https://www.zerorpc.io/

> One RPC to rule them all, One RPC to find them, One RPC to bring them all, and in the darkness bind them.

# install

- python -m venv your-dir
- cd your-dir
- ./bin/pip install lotrpc

## install head

- python -m venv your-dir
- cd your-dir
- ./bin/pip install -e "git+https://github.com/wtnb75/lotrpc.git#egg=lotrpc"

# Usage

## client-server example

- xmlrpc
  - ./bin/python -m lotrpc.clsrv server xml
  - ./bin/python -m lotrpc.clsrv client xml
- json-rpc
  - ./bin/python -m lotrpc.clsrv server json
  - ./bin/python -m lotrpc.clsrv client json
      - curl -X POST -d '{"method":"hello", "jsonrpc":"2.0", "params":["a","b","c"]}' http://localhost:9999/
- msgpack-rpc
  - ./bin/python -m lotrpc.clsrv server msgpack
  - ./bin/python -m lotrpc.clsrv client msgpack
- msgpack-rpc with mprpc
  - ./bin/python -m lotrpc.clsrv server mp
  - ./bin/python -m lotrpc.clsrv client mp
- grpc
  - ./bin/python -m lotrpc.clsrv server grpc --options '{"source":"examples/grpc/hello.proto"}'
  - ./bin/python -m lotrpc.clsrv client grpc --options '{"source":"examples/grpc/hello.proto"}' --method Greeter.SayHello --params '{"name":"xyzxyz"}'
- zerorpc
  - ./bin/python -m lotrpc.clsrv server zero
  - ./bin/python -m lotrpc.clsrv client zero
      - ./bin/zerorpc --json tcp://localhost:9999 hello '{"hello":"world"}'

## client usage (CLI)

```
# ./bin/python -m lotrpc.clsrv
Usage: clsrv.py [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  benchmark     start benchmark client
  client        serialized client
  client-async  client with asyncio
  client-pool   client with thread pool
  client-ppool  client with process pool
  listmode      list rpc mode
  proxy         start proxy server
  proxy-auth    start proxy with authentication example
  server        start server

# ./bin/python -m lotrpc.clsrv client --help
Usage: clsrv.py client [OPTIONS] [MODE] [ADDR]

  serialized client

Options:
  --options TEXT
  --num INTEGER
  --method TEXT
  --params TEXT
  --verbose / --no-verbose
  --help                    Show this message and exit.

# ./bin/python -m lotrpc.clsrv client json http://localhost:9999/endpoint --method hello --params '{"hello":"world"}'

# nc -l 9999
POST /endpoint HTTP/1.1
Host: localhost:9999
User-Agent: python-requests/2.21.0
Accept-Encoding: gzip, deflate
Accept: */*
Connection: keep-alive
content-type: application/json
Content-Length: 76

{"method": "hello", "params": {"hello": "world"}, "jsonrpc": "2.0", "id": 0}
```

## client usage (Python)

```python
import lotrpc

# JSON RPC
cl = lotrpc.json.Client("http://localhost:9999/endpoint")

# XML-RPC
cl = lotrpc.xml.Client("http://localhost:9999/endpoint")

# MessagePack-RPC
cl = lotrpc.msgpack.Client("http://localhost:9999/endpoint")

# ZeroRPC
cl = lotrpc.zero.Client("http://localhost:9999/endpoint")

## call it
res = cl.call("hello", {"hello": "world"})
print(res)
```

## server(dispatcher) usage (Python)

```python
import lotrpc

class HelloDispatcher(lotrpc.SimpleDispatcher):
    def do_hello(self, params):
        return {"result": "OK1"}

    def do_goodbye(self, params):
        return {"result": "OK2"}

# JSON RPC
srv = lotrpc.json.Server("http://localhost:9999/endpoint")

# XML-RPC
srv = lotrpc.xml.Server("http://localhost:9999/endpoint")

# MessagePack-RPC
srv = lotrpc.msgpack.Server("http://localhost:9999/endpoint")

# ZeroRPC
srv = lotrpc.zero.Server("http://localhost:9999/endpoint")

## serve it
srv.serve(HelloDispatcher())
```

## proxy

- (client) -> xmlrpc -(proxy)-> jsonrpc (server)
  - ./bin/python -m lotrpc.clsrv proxy xml http://localhost:9999/ json http://localhost:9998/
  - ./bin/python -m lotrpc.clsrv server json http://localhost:9998/
  - ./bin/python -m lotrpc.clsrv client xml http://localhost:9999/

## does not work...

- client
    - grpc + process pool
    - msgpack + thread pool, process pool, asyncio
    - xml + thread pool, process pool, asyncio
    - zero + thread pool, process pool, asyncio
    - aioxml + thread pool, process pool, asyncio
- server
    - aioxml

## TODO

- Work in Progress
    - aiohttp_xmlrpc
    - Sun RPC
        - (for test) ./bin/python -m lotrpc.rpcgen
- Golang net/rpc
- BSON RPC
- thrift
- Java RMI
