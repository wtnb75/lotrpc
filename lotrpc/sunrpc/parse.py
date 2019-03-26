import io
import keyword

from ply import lex
from ply import yacc

from logging import getLogger, basicConfig, DEBUG, INFO

log = getLogger(__name__)

reserved = """
CONST ENUM STRUCT OPAQUE UNSIGNED STRING TYPEDEF CASE DEFAULT VOID
UNION SWITCH BOOL HYPER LONG INT NETOBJ TRUE FALSE
PROGRAM VERSION
""".strip().split()

tokens = reserved + """
ID TYPEID ICONST
EQ LT GT MINUS PLUS TIMES
SEMI COLON COMMA
LPAREN RPAREN
LBRACKET RBRACKET
LBRACE RBRACE
""".strip().split()

t_ignore = " \t\x0c"

ngname = keyword.kwlist + dir(__builtins__)


def t_NEWLINE(t):
    r'\n+'


t_TIMES = r'\*'
t_MINUS = r'\-'
t_PLUS = r'\+'
t_LT = r'<'
t_GT = r'>'
t_EQ = r'='
t_LPAREN = r'\('
t_RPAREN = r'\)'
t_LBRACKET = r'\['
t_RBRACKET = r'\]'
t_LBRACE = r'\{'
t_RBRACE = r'\}'
t_COMMA = r','
t_SEMI = r';'
t_COLON = r':'
t_ICONST = r'[-+]?(0x?)?\d+'
t_ignore_COMMENT = r'(/\*(.|\n)*?\*/|//[^\n]*\n$)'
t_ignore_PP = r'\#(.)*?\n'
t_ignore_PX = r'\%(.)*?\n'

reserved_map = {
    "TRUE": "ICONST",
    "FALSE": "ICONST",
}
for r in reserved:
    reserved_map[r.lower()] = r

constmap = {}


def t_error(t):
    log.error("error: %s", t)


def t_ID(t):
    r'[A-Za-z_][\w_]*'
    t.type = reserved_map.get(t.value, "ID")
    while t.value in ngname:
        t.value = t.value + "_"
    return t


def sequence(t, first, second):
    if len(t) == first + 1:
        t[0] = [t[first]]
    elif len(t) == second + 1:
        if t[0] is None:
            t[0] = [t[first]]
            if t[second] is not None:
                t[0].extend(t[second])
        else:
            t[0].append(t[first])


def valmap(s):
    return dict(s)


def p_statements_1(t):
    """statements : statement statements
                  | statement"""
    log.debug("p_statements_1: %s", t)
    sequence(t, 1, 2)


def p_statement(t):
    """statement : defconst SEMI
                 | defenum SEMI
                 | defstruct SEMI
                 | typedef SEMI
                 | union SEMI
                 | program SEMI"""
    log.debug("p_statement_1: %s", t)
    t[0] = t[1]


def p_defconst(t):
    """defconst : CONST ID EQ ICONST"""
    log.debug("defconst: %s %s", t[2], t[4])
    reserved_map[t[2]] = "ICONST"
    constmap[t[2]] = t[4]
    t[0] = {"const": t[2], "value": t[4]}


def p_defenum(t):
    """defenum : ENUM ID LBRACE enuments RBRACE"""
    log.debug("p_defenum: %s %s", t[2], t[4])
    reserved_map[t[2]] = "TYPEID"
    t[0] = {"enum": t[2], "values": valmap(t[4])}


def p_enuments(t):
    """enuments : enument
                | enument COMMA enuments"""
    log.debug("p_enuments_1: %s", list(t))
    sequence(t, 1, 3)


def p_enument(t):
    """enument : ID EQ ICONST"""
    log.debug("p_enuments_2: %s %s", t[1], t[3])
    reserved_map[t[1]] = "ICONST"
    t[0] = (t[1], t[3])


def p_struct(t):
    """defstruct : STRUCT ID LBRACE structents RBRACE
                 | STRUCT TYPEID LBRACE structents RBRACE"""
    log.debug("p_struct: %s", t[2])
    reserved_map[t[2]] = "TYPEID"
    t[0] = {"struct": t[2], "entries": t[4]}


def p_structents(t):
    """structents : structent structents
                  | structent"""
    log.debug("p_structents: %s", list(t))
    sequence(t, 1, 2)


def p_structent_1(t):
    """structent : typeid ID SEMI
                 | typeid TYPEID SEMI
                 | ID ID SEMI"""
    log.debug("p_structent_1: %s %s", t[1], t[2])
    t[0] = {"name": t[2], "type": t[1], "note": "raw"}


def p_structent_2(t):
    """structent : typeid ID LT ICONST GT SEMI
                 | typeid ID LT GT SEMI
                 | typeid ID LBRACKET ICONST RBRACKET SEMI
                 | typeid ID LBRACKET RBRACKET SEMI"""
    log.debug("p_structent_2: %s", list(t))
    t[0] = {"name": t[2], "type": t[1], "note": "array"}
    if len(t) == 7:
        t[0]["length"] = t[4]
    if t[3] == "[":
        t[0]["fixed"] = True


def p_structent_3(t):
    """structent : ID TIMES ID SEMI
                 | typeid TIMES ID SEMI"""
    log.debug("p_structent_3: %s", list(t))
    t[0] = {"name": t[3], "type": t[1], "note": "pointer"}


def p_typeid(t):
    """typeid : TYPEID
              | OPAQUE
              | UNSIGNED
              | UNSIGNED HYPER
              | UNSIGNED INT
              | UNSIGNED LONG
              | STRING
              | NETOBJ
              | BOOL
              | HYPER
              | LONG
              | INT
              | VOID
              | STRUCT TYPEID"""
    log.debug("p_typeid: %s", t[1])
    t[0] = t[1]


def p_typedef_1(t):
    """typedef : TYPEDEF typeid ID
               | TYPEDEF typeid TYPEID
               | TYPEDEF typeid ID LT ICONST GT
               | TYPEDEF typeid ID LT GT
               | TYPEDEF typeid ID LBRACKET ICONST RBRACKET"""
    log.debug("p_typedef: %s", t[3])
    reserved_map[t[3]] = "TYPEID"
    t[0] = {"typedef": t[3], "type": t[2]}
    if len(t) == 4:
        t[0]["note"] = "raw"
    else:
        t[0]["note"] = "array"
    if len(t) == 7:
        t[0]["length"] = t[5]
    if len(t) > 5 and t[4] == "[":
        t[0]["fixed"] = True


def p_typedef_2(t):
    """typedef : TYPEDEF STRUCT ID TIMES ID"""
    log.debug("p_typedef_2: %s %s", t[3], t[5])
    reserved_map[t[5]] = "TYPEID"
    t[0] = {"typedef": t[3], "type": t[5], "note": "pointer"}


def p_union(t):
    """union : UNION ID SWITCH LPAREN typeid ID RPAREN LBRACE cases RBRACE"""
    log.debug("p_union: %s %s", t[2], t[5])
    reserved_map[t[2]] = "TYPEID"
    t[0] = {"union": t[2], "cond": {"type": t[5], "name": t[6]}, "cases": t[9]}


def p_cases(t):
    """cases : case cases
             | case"""
    log.debug("p_cases: %s", list(t))
    sequence(t, 1, 2)


def p_case(t):
    """case : caselabel typeid SEMI
            | caselabel
            | caselabel ID SEMI
            | caselabel ID ID SEMI
            | caselabel typeid ID SEMI"""
    log.debug("p_case: %s", t[1])
    t[0] = {"label": t[1]}
    if len(t) != 2:
        t[0]["type"] = t[2]
    if len(t) == 5:
        t[0]["name"] = t[3]


def p_caselabel_1(t):
    """caselabel : CASE ICONST COLON"""
    log.debug("p_caselabel: %s", t[2])
    t[0] = t[2]


def p_caselabel_2(t):
    """caselabel : DEFAULT COLON"""
    log.debug("p_caselabel: %s", t[1])
    t[0] = t[1]


def p_program(t):
    """program : PROGRAM ID LBRACE versions RBRACE EQ ICONST"""
    log.debug("p_program: %s %s %s", t[2], t[4], t[7])
    t[0] = {"program": t[2], "num": t[7], "versions": t[4]}


def p_versions(t):
    """versions : version versions
                | version"""
    log.debug("p_versions: %s", list(t))
    sequence(t, 1, 2)


def p_version(t):
    """version : VERSION ID LBRACE procs RBRACE EQ ICONST SEMI"""
    log.debug("p_version: %s id=%s procs=%s", t[2], t[7], t[4])
    t[0] = {"version": t[2], "num": t[7], "procs": t[4]}


def p_procs(t):
    """procs : proc procs
             | proc"""
    log.debug("p_procs: %s", list(t))
    sequence(t, 1, 2)


def p_proc(t):
    """proc : typeid ID LPAREN typeid RPAREN EQ ICONST SEMI"""
    log.debug("p_proc: %s id=%s arg=%s res=%s", t[2], t[7], t[4], t[1])
    t[0] = {"id": t[7], "name": t[2], "arg": t[4], "res": t[1]}


def p_error(t):
    log.error("error: %s", t)


def parse_file(fp, debug=False, defines={}):
    log.debug("defines: %s", defines)
    for k, v in defines.items():
        log.info("const: %s=%s", k, v)
        constmap[k] = str(v)
        if isinstance(v, int):
            reserved_map[k] = "ICONST"
            log.debug("reserved: %s=%s", k, v)
    lexer = lex.lex()
    parser = yacc.yacc(debug=debug)
    if not hasattr(fp, "encoding"):
        fp = io.TextIOWrapper(fp)
    return yacc.parse(fp.read(), debug=debug)


def get_lexer(fp):
    lx = lex.lex()
    lx.input(fp.read())
    return lx


if __name__ == "__main__":
    import sys
    import yaml
    basicConfig(level=DEBUG)
    mode = "lex"
    defs = {"LM_MAXSTRLEN": 1024, "MAXNAMELEN": 1025, "MAXNETNAMELEN": 255}
    # defs = {}
    if len(sys.argv) >= 2:
        mode = sys.argv[1]
    if mode == "lex":
        for token in get_lexer(sys.stdin):
            log.info("token %s", token)
    elif mode == "yacc":
        result = parse_file(sys.stdin, debug=True, defines=defs)
        log.debug("parsed %s", result)
        log.info("const %s", constmap)
        sys.stdout.write(yaml.dump(result))
    elif mode == "yacc_cpp":
        import subprocess
        with subprocess.Popen(["cpp"], stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE) as p:
            p.stdin.write(sys.stdin.read().encode('utf-8'))
            p.stdin.close()
            result = parse_file(p.stdout, debug=False, defines=defs)
        log.debug("parsed %s", result)
        log.info("const %s", constmap)
        sys.stdout.write(yaml.dump(result))
