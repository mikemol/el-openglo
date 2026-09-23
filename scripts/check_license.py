#!/usr/bin/env python3
"""check_license.py — MEASURE every place this project DECLARES its licence (W44).

The operator relicensed the project GPL-3 -> Apache-2.0 (2026-09-22). A licence
is declared in three kinds of place, and each is measured structurally:

    authority  emitters.LICENSE_SPDX — the one constant every generator imports
    generator  each module in emitters.ROLES, by AST: a dict key "License"
               (KPackage metadata.json) and a `License=` / `X-KDE-PluginInfo-License=`
               line in a str or f-string (.desktop / SDDM metadata). Per site: the
               id it resolves to, and `via` — "LICENSE_SPDX" when it names the
               constant, "literal" when it spells an id, "unresolved" otherwise
    file       LICENSE (the text, recognised by its heading), pyproject.toml
               [project].license, and the el-openglo ebuild's LICENSE=

    scripts/check_license.py --json      # the measurement (policy/license.rego decides)
    scripts/check_license.py --list      # every declaration, then n of m Apache-2.0
    scripts/check_license.py --selftest  # the measurement can SEE a GPL declaration

The requirement is policy/license.rego, run through `scripts/opa_gate.py license`.

⚑ THIRD-PARTY LICENCES ARE NOT IN THE POPULATION, DELIBERATELY, and are listed
under `third_party` in --json so the exclusion is visible rather than silent:
overlay/dev-python/colorspacious (upstream's ebuild), make_kvantum's KvFlat
(GPL-family; a recolour is a derived work and keeps upstream's licence), DSEG
(OFL; only named in make_font's note, never shipped) and Liberation Mono (OFL;
the marquee's glyphs are rasterised from it at build time).

WEAKNESS, STATED. This reads the GENERATORS, not their output: an emitted
metadata.json written by a stale run still says whatever that run wrote (the
main tree regenerates it). A declaration built by a shape this walker does not
know — a key assembled at run time, a licence in a template file — is outside
the population; templates/ carries none today (read, 2026-09-22), and a
generator that grows one in a new shape is invisible until this learns it.
"""
import ast
import json
import os
import re
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

CONSTANT = "LICENSE_SPDX"
EBUILD_DIR = os.path.join("overlay", "x11-themes", "el-openglo")
LINE = re.compile(r"(?:^|\n)(?:X-KDE-PluginInfo-)?License=([^\n]*)")
THIRD_PARTY = [
    {"what": "overlay/dev-python/colorspacious", "licence": "MIT (upstream's ebuild)"},
    {"what": "KvFlat, recoloured by make_kvantum", "licence": "GPL-family (upstream's, preserved)"},
    {"what": "DSEG fonts, named in make_font.DSEG_NOTE", "licence": "OFL-1.1 (not shipped)"},
    {"what": "Liberation Mono, rasterised by make_notify_marquee", "licence": "OFL-1.1 (build input)"},
]


def _names_constant(node):
    return (isinstance(node, ast.Name) and node.id == CONSTANT) or \
           (isinstance(node, ast.Attribute) and node.attr == CONSTANT)


def generator_sites(source, spdx):
    """[(line, id, via)] — every licence declaration in one module's source."""
    tree = ast.parse(source)
    out, inside_fstring = [], set()
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            parts = node.values
            for i, part in enumerate(parts):
                if not isinstance(part, ast.Constant):
                    continue
                inside_fstring.add(id(part))
                for m in LINE.finditer(part.value):
                    if m.group(1):                       # literal id inside an f-string
                        out.append((node.lineno, m.group(1), "literal"))
                    else:                                # `License=` then a hole
                        nxt = parts[i + 1] if i + 1 < len(parts) else None
                        if isinstance(nxt, ast.FormattedValue) and _names_constant(nxt.value):
                            out.append((node.lineno, spdx, CONSTANT))
                        else:
                            out.append((node.lineno, None, "unresolved"))
        elif isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == "License":
                    if _names_constant(v):
                        out.append((k.lineno, spdx, CONSTANT))
                    elif isinstance(v, ast.Constant) and isinstance(v.value, str):
                        out.append((k.lineno, v.value, "literal"))
                    else:
                        out.append((k.lineno, None, "unresolved"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                and id(node) not in inside_fstring:
            for m in LINE.finditer(node.value):
                out.append((node.lineno, m.group(1) or None, "literal"))
    return sorted(out, key=lambda s: s[0])


def licence_text_id(text):
    """The SPDX id a LICENSE text is, recognised by its heading; None if unrecognised."""
    head = " ".join(text.split()[:40])
    if "Apache License" in head and "Version 2.0" in head:
        return "Apache-2.0"
    if "GNU GENERAL PUBLIC LICENSE" in head and "Version 3" in head:
        return "GPL-3.0"
    if "GNU GENERAL PUBLIC LICENSE" in head and "Version 2" in head:
        return "GPL-2.0"
    return None


def ebuild_id(text):
    m = re.search(r'^LICENSE="([^"]*)"', text, re.M)
    return m.group(1) if m else None


def measure():
    import emitters as E
    spdx = getattr(E, CONSTANT, None)
    cases = [{"kind": "authority", "where": f"emitters.{CONSTANT}", "id": spdx, "via": "constant"}]
    roster = sorted(E.ROLES)
    declaring = 0
    for mod in roster:
        path = os.path.join(ROOT, mod + ".py")
        if not os.path.isfile(path):
            continue                                     # emitters --drift owns absence
        sites = generator_sites(open(path, encoding="utf-8").read(), spdx)
        declaring += bool(sites)
        cases += [{"kind": "generator", "where": f"{mod}.py:{ln}", "id": i, "via": via}
                  for ln, i, via in sites]
    lic = os.path.join(ROOT, "LICENSE")
    cases.append({"kind": "file", "where": "LICENSE", "via": "text",
                  "id": licence_text_id(open(lic, encoding="utf-8").read()) if os.path.isfile(lic) else None})
    pp = os.path.join(ROOT, "pyproject.toml")
    with open(pp, "rb") as fh:
        cases.append({"kind": "file", "where": "pyproject.toml [project].license", "via": "toml",
                      "id": tomllib.load(fh).get("project", {}).get("license")})
    ed = os.path.join(ROOT, EBUILD_DIR)
    for fn in sorted(os.listdir(ed)) if os.path.isdir(ed) else []:
        if fn.endswith(".ebuild"):
            cases.append({"kind": "file", "where": f"{EBUILD_DIR}/{fn} LICENSE=", "via": "ebuild",
                          "id": ebuild_id(open(os.path.join(ed, fn), encoding="utf-8").read())})
    return {"cases": cases, "roster": len(roster), "roster_declaring": declaring,
            "third_party": THIRD_PARTY}


def main(argv):
    known = {"--json", "--list", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_license: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    if "--list" in argv:
        m = measure()
        for c in m["cases"]:
            print(f"  {c['kind']:9s} {str(c['id']):12s} {c['via']:12s} {c['where']}")
        good = sum(c["id"] == "Apache-2.0" for c in m["cases"])
        print(f"\ncheck_license: {good} of {len(m['cases'])} declaration(s) are Apache-2.0; "
              f"{m['roster_declaring']} of {m['roster']} roster module(s) declare one; "
              f"{len(m['third_party'])} third-party licence(s) excluded (--json lists them)")
        return 0
    print("usage: check_license.py --json | --list | --selftest  "
          "(the verdict: scripts/opa_gate.py license)", file=sys.stderr)
    return 2


GPL_FIXTURE = '''
def meta():
    return {"KPlugin": {"License": "GPLv3"}}
def desk():
    return "[Desktop Entry]\\nX-KDE-PluginInfo-License=GPLv3\\n"
def sddm(v):
    return (f"Name={v}\\n" "License=GPL-3\\n")
'''
GOOD_FIXTURE = '''
from emitters import LICENSE_SPDX
def meta():
    return {"KPlugin": {"License": LICENSE_SPDX}}
def sddm(v):
    return f"Name={v}\\nLicense={LICENSE_SPDX}\\n"
'''


def _selftest():
    """The measurement can SEE: GPL spelled three ways is found as three literal GPL
    sites; the constant form resolves to the authority's id; a GPL LICENSE text is
    GPL; and the real tree's population is non-empty in every kind."""
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    bad = generator_sites(GPL_FIXTURE, "Apache-2.0")
    chk("a GPL fixture: three literal GPL sites seen",
        [(i, v) for _l, i, v in bad], [("GPLv3", "literal"), ("GPLv3", "literal"), ("GPL-3", "literal")])
    good = generator_sites(GOOD_FIXTURE, "Apache-2.0")
    chk("the constant form resolves to the authority",
        [(i, v) for _l, i, v in good], [("Apache-2.0", CONSTANT)] * 2)
    chk("a GPL-3 LICENSE text is GPL-3.0",
        licence_text_id("                    GNU GENERAL PUBLIC LICENSE\n  Version 3, 29 June 2007\n"), "GPL-3.0")
    chk("an Apache LICENSE text is Apache-2.0",
        licence_text_id("  Apache License\n  Version 2.0, January 2004\n"), "Apache-2.0")
    chk("an ebuild LICENSE= is read", ebuild_id('EAPI=8\nLICENSE="GPL-3"\n'), "GPL-3")
    m = measure()
    chk("every population kind is non-empty",
        sorted({c["kind"] for c in m["cases"]}), ["authority", "file", "generator"])
    print("check_license selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv))
