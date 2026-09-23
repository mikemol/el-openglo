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
    emitted    every TRACKED (`git ls-files`) generated file that declares one:
               a *.json parsed by json, any "License" key at any depth
               (KPackage metadata.json); a *.desktop parsed as a desktop entry
               (configparser), `License` / `X-KDE-PluginInfo-License` in any group

    scripts/check_license.py --json      # the measurement (policy/license.rego decides)
    scripts/check_license.py --list      # every declaration, then n of m per kind
    scripts/check_license.py --selftest  # the measurement can SEE a GPL declaration
    scripts/check_license.py --gate      # policy/license.rego's verdict (opa_gate's
                                         # evaluate + verdict), exit 0 / 1 / 3
    scripts/check_license.py --root DIR --json|--list|--gate
                                         # measure another checkout (e.g. a worktree
                                         # of an old commit) instead of this tree

Why `emitted` exists: the W44 relicense changed make_clock, and the TRACKED
plasma-clock/org.el.segclock/metadata.json still said "GPLv3" — the generator
kinds admitted, and only `git status` noticed. The generator is the cause; the
tracked output is what ships, so both are measured.

The requirement is policy/license.rego, run through `scripts/opa_gate.py license`.

⚑ THIRD-PARTY LICENCES ARE NOT IN THE POPULATION, DELIBERATELY, and are listed
under `third_party` in --json so the exclusion is visible rather than silent:
overlay/dev-python/colorspacious (upstream's ebuild), make_kvantum's KvFlat
(GPL-family; a recolour is a derived work and keeps upstream's licence), DSEG
(OFL; only named in make_font's note, never shipped) and Liberation Mono (OFL;
the marquee's glyphs are rasterised from it at build time).

WEAKNESS, STATED. `emitted` sees TRACKED output only: an untracked emitted file
(the main tree regenerates many) is outside it, and only *.json / *.desktop are
parsed — a licence in another tracked format (an XML, a .conf) is invisible
until a reader for it is added. A tracked *.json / *.desktop that fails to
parse is counted in `emitted_unparsed`, not judged. For generators, a declaration built by a shape this walker does not
know — a key assembled at run time, a licence in a template file — is outside
the population; templates/ carries none today (read, 2026-09-22), and a
generator that grows one in a new shape is invisible until this learns it.
"""
import ast
import configparser
import json
import os
import re
import subprocess
import sys
import tempfile
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
# The tracked paths of THIRD_PARTY above, excluded from the `emitted` population.
THIRD_PARTY_PATHS = ["overlay/dev-python/colorspacious"]


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


DESKTOP_KEYS = ("License", "X-KDE-PluginInfo-License")


def tracked_files(root):
    """Every path git tracks under `root`, relative to it."""
    out = subprocess.run(["git", "-C", root, "ls-files", "-z"], check=True,
                         capture_output=True).stdout.decode("utf-8")
    return [p for p in out.split("\0") if p]


def _third_party(rel):
    return any(rel == p or rel.startswith(p + "/") for p in THIRD_PARTY_PATHS)


def _json_licences(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            here = f"{path}.{k}" if path else k
            if k == "License":
                yield here, v if isinstance(v, str) else None
            else:
                yield from _json_licences(v, here)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _json_licences(v, f"{path}[{i}]")


def emitted_sites(root, paths):
    """([case], scanned, unparsed) — licence declarations in tracked emitted files."""
    cases, scanned, unparsed = [], 0, []
    for rel in sorted(paths):
        if _third_party(rel) or not rel.endswith((".json", ".desktop")):
            continue
        full = os.path.join(root, rel)
        if not os.path.isfile(full):
            continue
        scanned += 1
        try:
            text = open(full, encoding="utf-8").read()
            if rel.endswith(".json"):
                found = [(f"{rel} {k}", v, "json") for k, v in _json_licences(json.loads(text))]
            else:
                cp = configparser.ConfigParser(interpolation=None, strict=False)
                cp.optionxform = str
                cp.read_string(text)
                found = [(f"{rel} [{s}] {k}=", cp[s][k], "desktop")
                         for s in cp.sections() for k in DESKTOP_KEYS if k in cp[s]]
        except (ValueError, configparser.Error, UnicodeDecodeError):
            unparsed.append(rel)
            continue
        cases += [{"kind": "emitted", "where": w, "id": i, "via": via} for w, i, via in found]
    return cases, scanned, unparsed


def measure(root=None):
    root = os.path.abspath(root or ROOT)
    sys.path.insert(0, root)                             # this tree's emitters, not ours
    import emitters as E
    spdx = getattr(E, CONSTANT, None)
    cases = [{"kind": "authority", "where": f"emitters.{CONSTANT}", "id": spdx, "via": "constant"}]
    roster = sorted(E.ROLES)
    declaring = 0
    for mod in roster:
        path = os.path.join(root, mod + ".py")
        if not os.path.isfile(path):
            continue                                     # emitters --drift owns absence
        sites = generator_sites(open(path, encoding="utf-8").read(), spdx)
        declaring += bool(sites)
        cases += [{"kind": "generator", "where": f"{mod}.py:{ln}", "id": i, "via": via}
                  for ln, i, via in sites]
    lic = os.path.join(root, "LICENSE")
    cases.append({"kind": "file", "where": "LICENSE", "via": "text",
                  "id": licence_text_id(open(lic, encoding="utf-8").read()) if os.path.isfile(lic) else None})
    pp = os.path.join(root, "pyproject.toml")
    with open(pp, "rb") as fh:
        cases.append({"kind": "file", "where": "pyproject.toml [project].license", "via": "toml",
                      "id": tomllib.load(fh).get("project", {}).get("license")})
    ed = os.path.join(root, EBUILD_DIR)
    for fn in sorted(os.listdir(ed)) if os.path.isdir(ed) else []:
        if fn.endswith(".ebuild"):
            cases.append({"kind": "file", "where": f"{EBUILD_DIR}/{fn} LICENSE=", "via": "ebuild",
                          "id": ebuild_id(open(os.path.join(ed, fn), encoding="utf-8").read())})
    emitted, scanned, unparsed = emitted_sites(root, tracked_files(root))
    cases += emitted
    return {"root": root, "cases": cases, "roster": len(roster), "roster_declaring": declaring,
            "emitted_scanned": scanned, "emitted_unparsed": unparsed,
            "third_party": THIRD_PARTY}


def main(argv):
    known = {"--json", "--list", "--selftest", "--gate"}
    args, root = list(argv[1:]), None
    if "--root" in args:
        i = args.index("--root")
        if i + 1 >= len(args) or not os.path.isdir(args[i + 1]):
            print("check_license: --root needs an existing directory", file=sys.stderr)
            return 2
        root = args[i + 1]
        del args[i:i + 2]
    for a in args:
        if a not in known:
            print(f"check_license: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in args:
        return 0 if _selftest() else 1
    if "--json" in args:
        print(json.dumps(measure(root), indent=1))
        return 0
    if "--gate" in args:                                 # opa_gate's verdict, on --root's tree
        from scripts import opa_gate                     # OURS: imported before --root joins sys.path
        sets = opa_gate.evaluate("license", measure(root))
        for kind in ("deny", "withheld"):
            for msg in sets.get(kind, []):
                print(f"check_license: {kind.upper()} {msg}")
        rc = opa_gate.verdict(sets)
        print(f"check_license: {root or ROOT}: {['ADMITTED', 'DENIED', '', 'WITHHELD'][rc]}")
        return rc
    if "--list" in args:
        m = measure(root)
        for c in m["cases"]:
            print(f"  {c['kind']:9s} {str(c['id']):12s} {c['via']:12s} {c['where']}")
        print(f"\ncheck_license: root {m['root']}")
        for kind in ("authority", "generator", "file", "emitted"):
            ks = [c for c in m["cases"] if c["kind"] == kind]
            print(f"  {kind:9s} {sum(c['id'] == 'Apache-2.0' for c in ks)} of {len(ks)} "
                  "declaration(s) are Apache-2.0")
        print(f"  {m['roster_declaring']} of {m['roster']} roster module(s) declare one; "
              f"{m['emitted_scanned']} tracked *.json/*.desktop scanned, "
              f"{len(m['emitted_unparsed'])} unparsed; "
              f"{len(m['third_party'])} third-party licence(s) excluded (--json lists them)")
        return 0
    print("usage: check_license.py [--root DIR] --json | --list | --selftest  "
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
    with tempfile.TemporaryDirectory() as d:
        pkg = os.path.join(d, "plasma-clock", "org.x")
        os.makedirs(pkg)
        with open(os.path.join(pkg, "metadata.json"), "w") as fh:
            json.dump({"KPlugin": {"Id": "org.x", "License": "GPLv3"}}, fh)
        with open(os.path.join(pkg, "metadata.desktop"), "w") as fh:
            fh.write("[Desktop Entry]\nName=x\nX-KDE-PluginInfo-License=GPL-3\n")
        tp = os.path.join(d, "overlay", "dev-python", "colorspacious")
        os.makedirs(tp)
        with open(os.path.join(tp, "x.json"), "w") as fh:
            json.dump({"License": "MIT"}, fh)
        with open(os.path.join(d, "untracked.json"), "w") as fh:
            json.dump({"License": "GPLv3"}, fh)
        subprocess.run(["git", "-C", d, "init", "-q"], check=True)
        subprocess.run(["git", "-C", d, "add", "plasma-clock", "overlay"], check=True)
        seen, scanned, unparsed = emitted_sites(d, tracked_files(d))
        chk("a tracked GPLv3 metadata.json and .desktop are SEEN; third-party and "
            "untracked are not",
            [(c["where"], c["id"]) for c in seen],
            [("plasma-clock/org.x/metadata.desktop [Desktop Entry] X-KDE-PluginInfo-License=", "GPL-3"),
             ("plasma-clock/org.x/metadata.json KPlugin.License", "GPLv3")])
        chk("2 of 2 tracked emitted candidates scanned, none unparsed", (scanned, unparsed), (2, []))
    m = measure()
    chk("every population kind is non-empty",
        sorted({c["kind"] for c in m["cases"]}), ["authority", "emitted", "file", "generator"])
    print("check_license selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv))
