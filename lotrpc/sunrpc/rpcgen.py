import sys
from logging import getLogger
from jinja2 import Template

from .parse import parse_file

log = getLogger(__name__)

tmpl = """
from collections import OrderedDict
import json
import xdrlib
from enum import Enum, EnumMeta


class DefEnumMeta(EnumMeta):
    def __call__(cls, value=None, *args, **kwargs):
        if value is None:
            return next(iter(cls))
        return super().__call__(value, *args, **kwargs)

{% if const|length != 0 %}
class Constant(Enum):
    'constant values'
    {%- for cn in const %}
    {{cn["const"]}} = {{cn["value"]}}
    {%- endfor %}
{%- endif %}
{% if enum|length != 0 %}

class xdr_enum(Enum, metaclass=DefEnumMeta):
    def pack(self, p):
        p.pack_int(self.value)

    @classmethod
    def unpack(cls, u):
        return cls(u.unpack_int())
{%- endif %}
{% if struct|length + union|length != 0 %}

class xdr_struct:
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=json_encoder)

    def to_dict(self) -> dict:
        res = {}
        for k, v in self._members.items():
            val = getattr(self, k)
            if hasattr(val, "to_dict"):
                res[k] = val.to_dict()
            else:
                res[k] = val
        return res

    @classmethod
    def from_dict(cls, d: dict):
        res = cls()
        for k, v in d.items():
            setattr(res, k, v)
        return res

    def to_binary(self) -> bytes:
        p = xdrlib.Packer()
        self.pack(p)
        return p.get_buf()

    @classmethod
    def from_binary(cls, data: bytes):
        u = xdrlib.Unpacker(data)
        res = cls.unpack(u)
        return res, data[u.get_position():]

    def pack(self, p):
        for k, v in self._members.items():
            val = getattr(self, k)
            if hasattr(p, "pack_{}".format(v)):
                fn = getattr(p, "pack_{}".format(v))
                fn(val)
            else:
                val.pack(p)

    @classmethod
    def unpack(cls, u):
        res = cls()
        for k, v in cls._members.items():
            if hasattr(u, "unpack_{}".format(v)):
                fn = getattr(u, "unpack_{}".format(v))
                setattr(res, k, fn())
            else:
                setattr(res, k, getattr(res, k).unpack(u))
        return res
{%- endif %}
{% if union|length != 0 %}

class xdr_union(xdr_struct):
    def to_dict(self) -> dict:
        res = {}
        val = getattr(self, self._cond)
        res[self._cond] = val
        if val in self._values:
            k = self._values[val]
            v = getattr(self, k)
            if hasattr(v, "to_dict"):
                res[k] = v.to_dict()
            else:
                res[k] = v
        return res

    def pack(self, p):
        val = getattr(self, self._cond)
        val.pack(p)
        if val in self._values:
            to_pack = getattr(self, self._values[val])
            to_pack.pack(p)

    @classmethod
    def unpack(cls, u):
        res = cls()
        cval = getattr(res, res._cond)
        setattr(res, res._cond, cval.unpack(u))
        cval = getattr(res, res._cond)
        if cval in cls._values:
            val = getattr(res, cls._values[cval])
            setattr(res, cls._values[cval], val.unpack(u))
        return res
{%- endif %}
{% if typedef|length != 0 %}

class xdr_typedef:
    def to_dict(self):
        return self.data
{%- endif %}


def json_encoder(obj):
{%- if enum|length != 0 %}
    if isinstance(obj, xdr_enum):
        return obj.name
{%- endif %}
{%- if union|length + struct|length != 0 %}
    if isinstance(obj, xdr_struct):
        return obj.to_dict()
{%- endif %}
{%- if typedef|length != 0 %}
    if isinstance(obj, xdr_typedef):
        return obj.data
{%- endif %}
    return obj
{% for tp in typedef %}

class {{tp["typedef"]}}(xdr_typedef):
    'typedef {{tp["typedef"]}}'

    def __init__(self):
        # {{tp}}
        self.data = None

    def pack(self, p):
        p.pack_{% if "fixed" in tp%}f{%endif%}{{tp["type"]}}(self.data)

    @classmethod
    def unpack(cls, u):
{%- if "fixed" in tp and tp["fixed"] %}
        self.data = u.unpack_f{{tp["type"]}}({{id2val[tp["length"]]}})
{%- else %}
        self.data = u.unpack_{{tp["type"]}}()
{%- endif %}
{% endfor -%}
{% for en in enum %}

class {{en["enum"]}}(xdr_enum):
    'enum {{en["enum"]}}'
    {%- for k,v in en["values"].items() %}
    {{k}} = {{v}}
    {%- endfor %}
{%- endfor %}
{% for st in struct %}

class {{st["struct"]}}(xdr_struct):
    'struct {{st["struct"]}}'
    _members = OrderedDict([
{%- for e in st["entries"] %}
        ("{{e["name"]}}", "{{basetype[e["type"]]|default(e["type"])}}"),
{%- endfor %}
    ])

    def __init__(self):
{%- for x in st["entries"] %}
        # {{x}}
{%- if x["type"] in basetype %}
        self.{{x["name"]}} = None
{%- else %}
        self.{{x["name"]}} = {{x["type"]}}()
{%- endif %}
{%- endfor %}
{% endfor -%}
{% for un in union %}

class {{un["union"]}}(xdr_union):
    'union {{un["union"]}}'
    _cond = "{{un["cond"]["name"]}}"
    _values = {
{%- for c in un["cases"] %}
{%- if "name" in c %}
{%- if c["label"] == "default" %}
        None: "{{c["name"]}}",
{%- else %}
        {{id2val[c["label"]] | default(c["label"])}}: "{{c["name"]}}",
{%- endif %}
{%- endif %}
{%- endfor %}
    }

    def __init__(self):
        # condition: {{un["cond"]}}
{%- if un["cond"]["type"] in basetype %}
        self.{{un["cond"]["name"]}} = None
{%- else %}
        self.{{un["cond"]["name"]}} = {{un["cond"]["type"]}}()
{%- endif %}
    {%- for c in un["cases"] %}
{%- if "name" in c %}
        # {{c}}
{%- if c["type"] in basetype %}
        self.{{c["name"]}} = None
{%- else %}
        self.{{c["name"]}} = {{c["type"]}}()
{%- endif %}
{%- endif %}
    {%- endfor %}
{% endfor %}
{%- for p in program %}

class {{p["program"]}}:
    'program {{p["program"]}}'
    ID = {{p["num"]}}
{% for v in p["versions"] %}
    class {{v["version"]}}:
        'version {{v["version"]}}'
        ID = {{v["num"]}}
{% for proc in v["procs"] %}
        def {{proc["name"]}}(self{% if proc["arg"] != "void" %}, arg: {{typemap[proc["arg"]]|default(proc["arg"])}}{% endif %}) -> {% if proc["res"]!="void" %}{{typemap[proc["res"]]|default(proc["res"])}}{% else %}None{% endif %}:
            pass
{% endfor %}
        pass
{% endfor %}
    pass
{% endfor %}
"""


def convert_parsed(parsed):
    res = {
        "const": [],
        "enum": [],
        "struct": [],
        "union": [],
        "program": [],
        "typedef": [],
        "id2val": {
            "TRUE": "True",
            "FALSE": "False",
        },
        "basetype": {
            "int": "int",
            "unsigned": "uint",
            "bool": "bool",
            "hyper": "hyper",
            "uhyper": "uhyper",
            "float": "float",
            "double": "double",
            "string": "string",
            "opaque": "opaque"
        },
        "typemap": {
            "unsigned": "int",
            "opaque": "bytes",
            "string": "str",
            "double": "float",
            "hyper": "int",
        }
    }
    for l in parsed:
        for k in res.keys():
            if l.get(k, None) is not None:
                res[k].append(l)
    for c in res["const"]:
        if c["value"].startswith("0") and not c["value"].startswith("0x"):
            c["value"] = "0o" + c["value"].lstrip("0")
        res["id2val"][c["const"]] = "Constant.{}".format(c["const"])
    for c in res["const"]:
        res["id2val"][c["const"]] = "Constant.{}".format(c["const"])
    for en in res["enum"]:
        for k, v in en["values"].items():
            res["id2val"][k] = "{}.{}".format(en["enum"], k)
    log.debug("converted: %s", res["struct"])
    return res


def generate_proto(parsed, tmpl_str=None):
    if tmpl_str is None:
        tmpl_str = tmpl
    template = Template(tmpl_str)
    res = template.render(convert_parsed(parsed))
    return res


if __name__ == "__main__":
    data = parse_file(sys.stdin)
    res = generate_proto(data)
    print(res)
