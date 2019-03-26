import os
import sys
import subprocess
import tempfile
import importlib
import click
import yaml
from logging import getLogger, basicConfig, DEBUG

import lotrpc.sunrpc.parse
import lotrpc.sunrpc.rpcgen


log = getLogger(__name__)


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        print(ctx.get_help())


@cli.command()
@click.argument("file", type=click.File('r'))
@click.option("--verbose/--no-verbose", default=False)
def lex(file, verbose):
    if verbose:
        basicConfig(level=DEBUG)
    for token in lotrpc.sunrpc.parse.get_lexer(file):
        log.info("token %s", token)


def parse_file(file, cpp, defs, verbose):
    defs = yaml.load(defs, Loader=yaml.FullLoader)
    if cpp is not None:
        with subprocess.Popen(["cpp"], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE) as p:
            p.stdin.write(file.read().encode('utf-8'))
            p.stdin.close()
            file = p.stdout
            return lotrpc.sunrpc.parse.parse_file(
                p.stdout, debug=verbose, defines=defs)

    return lotrpc.sunrpc.parse.parse_file(file, debug=verbose, defines=defs)


defdef = "{LM_MAXSTRLEN: 1024, MAXNAMELEN: 1025, MAXNETNAMELEN: 255}"


@cli.command()
@click.option("--cpp/--no-cpp", default=False)
@click.option("--defs", default=defdef)
@click.option("--verbose/--no-verbose", default=False)
@click.argument("file", type=click.File('r'))
def parse(file, cpp, defs, verbose):
    if verbose:
        basicConfig(level=DEBUG)
    result = parse_file(file, cpp, defs, verbose)
    print(yaml.dump(result))


@cli.command()
@click.option("--cpp/--no-cpp", default=False)
@click.option("--defs", default=defdef)
@click.option("--template", default=None, type=click.File('r'))
@click.option("--verbose/--no-verbose", default=False)
@click.argument("file", type=click.File('r'))
def rpcgen(file, cpp, defs, template, verbose):
    if verbose:
        basicConfig(level=DEBUG)
    data = parse_file(file, cpp, defs, verbose)
    tmpl = None
    if template is not None:
        tmpl = template.read()
    res = lotrpc.sunrpc.rpcgen.generate_proto(data, tmpl)
    print(res)


@cli.command()
@click.option("--cpp/--no-cpp", default=False)
@click.option("--defs", default=defdef)
@click.option("--template", default=None, type=click.File('r'))
@click.option("--verbose/--no-verbose", default=False)
@click.argument("file", type=click.File('r'))
def rpcgen_autopep(file, cpp, defs, template, verbose):
    if verbose:
        basicConfig(level=DEBUG)
    data = parse_file(file, cpp, defs, verbose)
    tmpl = None
    if template is not None:
        tmpl = template.read()
    res = lotrpc.sunrpc.rpcgen.generate_proto(data, tmpl)
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w") as tf:
        tf.write(res)
        with subprocess.Popen(["autopep8", "--diff", tf.name], stdin=subprocess.DEVNULL) as p:
            p.wait()


@cli.command()
@click.option("--cpp/--no-cpp", default=False)
@click.option("--defs", default=defdef)
@click.option("--template", default=None, type=click.File('r'))
@click.option("--verbose/--no-verbose", default=False)
@click.argument("file", type=click.File('r'))
def rpcgen_help(file, cpp, defs, template, verbose):
    if verbose:
        basicConfig(level=DEBUG)
    data = parse_file(file, cpp, defs, verbose)
    tmpl = None
    if template is not None:
        tmpl = template.read()
    with tempfile.TemporaryDirectory() as tmpd:
        with open(os.path.join(tmpd, "mymodule.py"), "w") as ofp:
            res = lotrpc.sunrpc.rpcgen.generate_proto(data, tmpl)
            ofp.write(res)
        sys.path.append(tmpd)
        mod = importlib.import_module("mymodule")
        help(mod)


if __name__ == '__main__':
    cli()
