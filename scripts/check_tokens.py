#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_tokens.py — the DTCG token file is well-formed, complete and current (W160).

    scripts/check_tokens.py            # the verdict, as opa_gate tokens decides it
    scripts/check_tokens.py --json     # the measurement policy/tokens.rego decides
    scripts/check_tokens.py --selftest # the measurement can see a bad leaf and a drift

Per declared variant (variant_roster, the palette authority): whether the committed
catalog/el-openglo.tokens.json has its group, how many colour and alpha leaves it
carries, and every leaf that is not valid DTCG (`color` must be `#rrggbb`, `number`
numeric, nothing else typed). Plus whether the committed file equals a fresh
make_tokens.document() - a stale token file is a file that no longer says the palette.

The `material` group (W151) is aliases: each must resolve in the file to a literal leaf
of its own $type; the case reports which material slots exist.

WEAKNESS: it checks the DTCG SHAPE this emitter uses (two types), not the whole DTCG
format; and it proves the file matches the emitter, not that a design tool imports it.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
HEX = re.compile(r"^#[0-9a-f]{6}$")
ALIAS = re.compile(r"^\{([^{}]+)\}$")


def resolve(doc, ref):
    """The leaf a DTCG alias path names in doc, or None."""
    node = doc
    for part in ref.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, dict) and "$value" in node else None


def bad_leaves(group, prefix="", doc=None):
    """[path] of every leaf in a DTCG group whose $type/$value is not this file's shape.
    An alias `{a.b.c}` is good only if it resolves in doc to a literal leaf of the same $type."""
    out = []
    for k, v in sorted(group.items()):
        if k.startswith("$"):
            continue
        path = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict) and "$value" in v:
            t, val = v.get("$type"), v.get("$value")
            m = ALIAS.match(val) if isinstance(val, str) else None
            if m:
                target = resolve(doc or {}, m.group(1))
                ok = (
                    target is not None
                    and target.get("$type") == t
                    and not (
                        isinstance(target["$value"], str)
                        and ALIAS.match(target["$value"])
                    )
                )
            else:
                ok = (
                    t == "color" and isinstance(val, str) and bool(HEX.match(val))
                ) or (
                    t == "number"
                    and isinstance(val, (int, float))
                    and not isinstance(val, bool)
                )
            if not ok:
                out.append(path)
        elif isinstance(v, dict):
            out.extend(bad_leaves(v, path, doc))
        else:
            out.append(path)
    return out


def measure(path=None):
    import variant_roster

    import make_tokens as MT

    path = path or MT.OUT
    roster = list(variant_roster.ids())
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as e:
        return {
            "roster": roster,
            "cases": [],
            "current": None,
            "withheld": [f"token file unreadable: {e}"],
        }
    cases = []
    for v in roster:
        g = doc.get(v)
        if not isinstance(g, dict):
            cases.append({"variant": v, "present": False})
            continue
        cases.append(
            {
                "variant": v,
                "present": True,
                "colors": len(g.get("color", {})),
                "alphas": len(g.get("alpha", {})),
                "materials": sorted(g.get("material", {})),
                "bad": bad_leaves(g, v, doc),
            }
        )
    return {
        "roster": roster,
        "cases": cases,
        "current": doc == MT.document(),
        "withheld": [],
    }


def _selftest():
    import tempfile

    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    chk(
        "a good group has no bad leaf",
        bad_leaves(
            {
                "color": {"fg": {"$type": "color", "$value": "#00ff00"}},
                "alpha": {"a": {"$type": "number", "$value": 0.4}},
            }
        ),
        [],
    )
    chk(
        "a non-hex colour is seen",
        bad_leaves({"color": {"fg": {"$type": "color", "$value": "0,255,0"}}}),
        ["color.fg"],
    )
    chk(
        "a string number is seen",
        bad_leaves({"alpha": {"a": {"$type": "number", "$value": "0.4"}}}),
        ["alpha.a"],
    )
    d = {
        "V": {
            "color": {"fg": {"$type": "color", "$value": "#00ff00"}},
            "material": {
                "e": {"$type": "color", "$value": "{V.color.fg}"},
                "x": {"$type": "color", "$value": "{V.color.nope}"},
                "n": {"$type": "number", "$value": "{V.color.fg}"},
            },
        }
    }
    chk(
        "an alias resolves; a dangling or type-mismatched alias is seen",
        bad_leaves(d["V"], "V", d),
        ["V.material.n", "V.material.x"],
    )
    import make_tokens as MT

    doc = MT.document()
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "t.json")
        with open(p, "w") as fh:
            json.dump(doc, fh)
        m = measure(p)
        chk(
            "a fresh document is current with every variant present",
            (m["current"], all(c["present"] for c in m["cases"])),
            (True, True),
        )
        first = min(k for k in doc if not k.startswith("$"))
        del doc[first]
        with open(p, "w") as fh:
            json.dump(doc, fh)
        m = measure(p)
        chk(
            "a dropped variant is seen absent, and the file reads stale",
            ([c["variant"] for c in m["cases"] if not c["present"]], m["current"]),
            ([first], False),
        )
    print("check_tokens selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    for a in argv[1:]:
        if a not in {"--json", "--selftest"}:
            print(f"check_tokens: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate

    return opa_gate.gate("tokens")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
