# gRPC Server/Client
import os
import sys
import shutil
import tempfile
import importlib
import time
import functools
import concurrent.futures
from logging import getLogger

from google.protobuf.json_format import MessageToDict, ParseDict
from google.protobuf.descriptor_pb2 import FileDescriptorSet
import grpc_tools.protoc
import grpc

from ..server import ServerIf
from ..client import ClientIf

log = getLogger(__name__)


def read_desc(src):
    with open(src, "rb") as f:
        return FileDescriptorSet.FromString(f.read())


def compile(src, dest):
    shutil.copyfile(src, os.path.join(dest, os.path.basename(src)))
    orgdir = os.getcwd()
    os.chdir(dest)
    bn = os.path.splitext(os.path.basename(src))[0]
    dsname = bn + ".pb"
    options = {
        "proto_path": ".",
        "python_out": ".",
        "grpc_python_out": ".",
        "descriptor_set_out": dsname,
    }
    arg = ["--%s=%s" % (x[0], x[1]) for x in options.items()]
    arg.append(os.path.basename(src))
    log.debug("pre-listdir %s", os.listdir(dest))
    log.debug("compile %s", arg)
    rst = grpc_tools.protoc.main(arg)
    log.debug("compile result: %s", rst)
    ret = read_desc(dsname)
    os.chdir(orgdir)
    return ret


def desc2typemap(desc):
    typemap = {}
    for f in desc.file:
        for sv in f.service:
            svname = sv.name
            for m in sv.method:
                name = m.name
                ityp = m.input_type
                otyp = m.output_type
                typemap[svname + "." + name] = {
                    "arg": ityp.split(".")[-1],
                    "return": otyp.split(".")[-1],
                }
    log.debug("typemap %s", typemap)
    return typemap


def do_import(src, dest):
    bn = os.path.splitext(os.path.basename(src))[0]
    modname = bn + "_pb2"
    modname = modname.replace("/", ".")
    log.debug("listdir %s", os.listdir(dest))
    sys.path.append(dest)
    log.debug("module load from %s %s", dest, modname)
    mod = importlib.import_module(modname)
    grpcmod = importlib.import_module(modname + "_grpc")
    log.debug("module %s %s", mod, grpcmod)
    return mod, grpcmod


def read_proto(src):
    tmpdir = tempfile.TemporaryDirectory()
    log.debug("tmpdir %s", tmpdir.name)
    desc = compile(src, tmpdir.name)
    typemap = desc2typemap(desc)
    mod, grpcmod = do_import(src, tmpdir.name)
    log.debug("moddir %s", dir(mod))
    log.debug("grpcmoddir %s", dir(grpcmod))
    for k, v in typemap.items():
        if hasattr(mod, v.get("arg")):
            typemap[k]["argtype"] = getattr(mod, v.get("arg"))
        if hasattr(mod, v.get("return")):
            typemap[k]["rettype"] = getattr(mod, v.get("return"))
    return desc, typemap, mod, grpcmod


class Server(ServerIf):
    def __init__(self, addr: str, params: dict = {}):
        super().__init__(addr, params)
        src = self.params.get("source", None)
        if src is not None:
            self.desc, self.typemap, self.mod, self.grpcmod = read_proto(src)
            log.debug("typemap %s", self.typemap)

    def mtd(yourself, myself, method, typeinfo, req, context):
        log.debug("method called you=%s, me=%s, method=%s, typeinfo=%s, req=%s, ctxt=%s",
                  yourself, myself, method, typeinfo, req, context)
        res = yourself.d(method, MessageToDict(req))
        restype = typeinfo.get("rettype")
        ret = ParseDict(res, restype())
        return ret

    def serve(self, dispatcher):
        self.d = dispatcher
        bn = list(set([x.split(".", 1)[0] for x in self.typemap.keys()]))[0]
        servicer = getattr(self.grpcmod, bn + "Servicer")
        funcs = {
            "d": dispatcher,
        }
        for k, v in self.typemap.items():
            fname = k.split(".", 1)[-1]
            log.debug("func: %s %s %s", fname, k, v)
            funcs[fname] = functools.partialmethod(self.mtd, k, v)
        log.debug("servicer: %s funcs=%s", bn, funcs)
        myservicer = type(bn + "Servicer", (servicer,), funcs)
        server = grpc.server(
            concurrent.futures.ThreadPoolExecutor(max_workers=10))
        addfn = getattr(self.grpcmod, "add_" + bn + "Servicer_to_server")
        log.debug("addfn: %s", addfn)
        addfn(myservicer(), server)
        server.add_insecure_port("%s:%s" % (
            self.addr_parsed.hostname, self.addr_parsed.port))
        log.debug("start server %s", server)
        server.start()
        try:
            while True:
                time.sleep(100)
        except KeyboardInterrupt:
            server.stop(0)


class Client(ClientIf):
    def __init__(self, addr: str, params: dict = {}):
        super().__init__(addr, params)
        src = self.params.get("source", None)
        if src is not None:
            self.desc, self.typemap, self.mod, self.grpcmod = read_proto(src)
            log.debug("typemap %s", self.typemap)
        self.channel = grpc.insecure_channel("%s:%s" % (
            self.addr_parsed.hostname, self.addr_parsed.port))

    def call(self, method: str, params=None):
        sig = self.typemap.get(method, {})
        log.debug("call %s %s sig=%s", method, params, sig)
        argtype = sig.get("argtype", None)
        restype = sig.get("rettype", None)
        if argtype is None or restype is None:
            raise Exception("no such method? %s" % (method))
        arg = ParseDict(params, argtype())
        svname, funcname = method.split(".", 1)
        log.debug("service=%s, func=%s", svname, funcname)
        stubcls = getattr(self.grpcmod, svname + "Stub")
        stub = stubcls(self.channel)
        mtd = getattr(stub, funcname)
        log.debug("method %s %s %s arg=%s", mtd, stub, funcname, arg)
        rsp = mtd(arg)
        return MessageToDict(rsp)
