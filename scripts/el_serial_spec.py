"""el_serial_spec.py — the ONE reading of guest/el-serial-spec.json (el-serial/1).

Imported by scripts/el_serial_emit.py (the reference writer) and
scripts/read_serial.py (the reader), so the writer and the reader cannot
disagree about a kind, a payload key or a type: neither names one itself.
guest/el-serial-emit.sh reads the same JSON with jq and applies the same
type table (its `type_ok` jq function mirrors `type_ok` here, arm for arm).

Weakness: the jq mirror is kept in step by review, not by construction; what
IS by construction is the table both sides read. No --selftest of its own:
read_serial.py --selftest and el_serial_emit.py --selftest exercise every arm.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC_PATH = os.path.join(ROOT, "guest", "el-serial-spec.json")

_PATTERNS = {
    "blob_id": re.compile(r"b(0|[1-9][0-9]*)"),
    "b64": re.compile(r"[A-Za-z0-9+/=]*"),
    "sha256": re.compile(r"[0-9a-f]{64}"),
    "boot_id": re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"),
}


def load(path=SPEC_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def canonical(obj):
    """The one serialisation: keys sorted at EVERY level, no spaces, ASCII only.
    jq's equivalent is `jq -cSa`."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def type_ok(spec, t, v):
    if t == "str":
        return isinstance(v, str)
    if t == "int":
        return isinstance(v, int) and not isinstance(v, bool) and v >= 0
    if t == "bool":
        return isinstance(v, bool)
    if t == "object":
        return isinstance(v, dict)
    if t in ("blob", "blob_id"):
        return isinstance(v, str) and _PATTERNS["blob_id"].fullmatch(v) is not None
    if t == "b64":
        return isinstance(v, str) and len(v) <= spec["part_b64_chars"] and _PATTERNS["b64"].fullmatch(v) is not None
    if t in ("sha256", "boot_id"):
        return isinstance(v, str) and _PATTERNS[t].fullmatch(v) is not None
    raise ValueError(f"el-serial spec names unknown type {t!r}")


def validate(spec, kind, obj):
    """[] when `obj` (envelope + payload) is a well-formed `kind` frame, else reasons."""
    if kind not in spec["kinds"]:
        return [f"unknown kind {kind!r}"]
    want = dict(spec["envelope"])
    want.update(spec["kinds"][kind])
    errs = []
    if set(obj) != set(want):
        errs.append(f"{kind}: keys {sorted(obj)} are not exactly {sorted(want)}")
    for k, t in sorted(want.items()):
        if k in obj and not type_ok(spec, t, obj[k]):
            errs.append(f"{kind}: {k}={obj[k]!r} is not a {t}")
    return errs
