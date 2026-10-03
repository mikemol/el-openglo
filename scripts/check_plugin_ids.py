#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_plugin_ids.py — every Plasma plugin id the install references is one it ships (W171).

⚑ WHY (operator, 2026-09-22, after emerging be318a6: "My plasma didn't come up at
all!"). The desktop containment named org.el.openglo.live.elazure, a wallpaper id
the one-package build no longer shipped; a missing WALLPAPER plugin fails the shell
(f521e6f). Every gate then read text or rendered pictures; none asked whether the
ids the install REFERENCES are ids the install DECLARES. This measures exactly that,
over the tree make_deb.stage() lays down — the one install set both packagers use.

    shipped     every metadata.json under usr/share/plasma/<kind>/<dir>/: its
                KPlugin.Id and whether that Id is its directory name (Plasma finds a
                package by directory; a mismatch loads under neither name reliably)
    referenced  every org.el.* id string in the staged non-metadata text (look-and-
                feel layouts and defaults, the shell update scripts, configs), with
                the file it appears in

    scripts/check_plugin_ids.py --json [--stage DIR]   # the measurement
    scripts/check_plugin_ids.py --list [--stage DIR]   # n of m referenced ids shipped
    scripts/check_plugin_ids.py --selftest
    scripts/opa_gate.py plugin_ids                     # the verdict (policy/plugin_ids.rego)

--stage DIR reads an already-staged tree (staging runs every emitter); without it a
temp dir is staged.

WEAKNESS, STATED. A reference is any `org.el.` token in staged text, so an id built
at run time from parts ("org.el." + name) is invisible, and a token in prose (a
comment naming an old id) is counted as a reference — the second errs toward
refusing, which is the safe side. Ids outside org.el.* (KDE's own) are not in the
population: this checks our ids only.
"""
import json
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PLASMA = os.path.join("usr", "share", "plasma")
SHARE = os.path.join("usr", "share")
# an id, and the character after it: a trailing "." then a non-id character (".$(",
# '." +') means the id is COMPLETED at run time - a PREFIX, not a reference
ID_RE = re.compile(r"\b(org\.el\.[a-z0-9]+(?:\.[a-z0-9]+)*)(\.(?![a-z0-9]))?")
TEXT_EXT = (".js", ".qml", ".json", ".desktop", ".conf", ".ini", ".rc", "")


def shipped_ids(stage):
    """[{id, kind, dir, dir_matches}] — every package metadata.json under usr/share:
    plasma's AND kwin's (W171 measured the task switcher at usr/share/kwin/tabbox/,
    which a plasma-only walk read as a dangling reference). `kind` is the path
    between usr/share and the package directory."""
    out = []
    base = os.path.join(stage, SHARE)
    # population: the staged install tree make_deb.stage() assembled, not the repo
    for dp, dirs, fs in os.walk(base):
        dirs.sort()
        if "metadata.json" not in fs:
            continue
        try:
            with open(os.path.join(dp, "metadata.json"), encoding="utf-8") as fh:
                pid = json.load(fh)["KPlugin"]["Id"]
        except (ValueError, KeyError, TypeError, OSError):
            continue                      # not a KPackage metadata file
        d = os.path.basename(dp)
        out.append({"id": pid, "kind": os.path.relpath(os.path.dirname(dp), base), "dir": d,
                    "dir_matches": pid == d})
        dirs[:] = []                      # a package's own subtree holds no further packages
    return sorted(out, key=lambda x: (x["kind"], x["dir"]))


def referenced_ids(stage):
    """[{id, file}] — every org.el.* token in staged text other than a metadata.json."""
    refs = set()
    # population: the staged install tree make_deb.stage() assembled, not the repo
    for dp, _dirs, fs in os.walk(stage):
        if os.path.relpath(dp, stage).split(os.sep)[0] == "DEBIAN":
            continue
        for f in fs:
            if f == "metadata.json" or os.path.splitext(f)[1] not in TEXT_EXT:
                continue
            p = os.path.join(dp, f)
            if os.path.islink(p) or not os.path.isfile(p):
                continue
            try:
                with open(p, encoding="utf-8") as fh:
                    text = fh.read()
            except (UnicodeDecodeError, OSError):
                continue
            for m in ID_RE.finditer(text):
                refs.add((m.group(1), "/" + os.path.relpath(p, stage), bool(m.group(2))))
    return [{"id": i, "file": f, "prefix": pre} for i, f, pre in sorted(refs)]


def measure(stage):
    if not os.path.isdir(os.path.join(stage, PLASMA)):
        return {"stage": stage, "shipped": [], "referenced": [],
                "withheld": f"{stage} has no {PLASMA}: not a staged install tree"}
    return {"stage": stage, "shipped": shipped_ids(stage), "referenced": referenced_ids(stage),
            "withheld": None}


def staged_measure(stage=None):
    if stage:
        return measure(stage)
    import make_deb
    with tempfile.TemporaryDirectory() as td:
        make_deb.stage(td)
        return measure(td)


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(("  ok   " if got == want else "  FAIL ") + label
              + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    def pkg(stage, kind, d, pid):
        p = os.path.join(stage, PLASMA, kind, d)
        os.makedirs(p)
        with open(os.path.join(p, "metadata.json"), "w") as fh:
            json.dump({"KPlugin": {"Id": pid}}, fh)

    with tempfile.TemporaryDirectory() as s:
        pkg(s, "wallpapers", "org.el.openglo.live", "org.el.openglo.live")
        pkg(s, "plasmoids", "org.el.segclock", "org.el.renamed")          # a renamed package
        lf = os.path.join(s, PLASMA, "look-and-feel", "x", "contents", "layouts")
        os.makedirs(lf)
        with open(os.path.join(lf, "org.kde.plasma.desktop-layout.js"), "w") as fh:
            fh.write(
                'd.wallpaperPlugin = "org.el.openglo.live";\n'
                'd.addWidget("org.el.openglo.live.elazure");\n'            # the f521e6f dangling id
                'p.addWidget("org.kde.plasma.digitalclock");\n')
        m = measure(s)
        ship = {x["id"]: x["dir_matches"] for x in m["shipped"]}
        chk("a package whose Id is not its directory is SEEN", ship.get("org.el.renamed"), False)
        chk("...and a matching one is not flagged", ship.get("org.el.openglo.live"), True)
        refd = sorted({r["id"] for r in m["referenced"]})
        chk("org.el.* references are read; KDE's own ids are not in the population",
            refd, ["org.el.openglo.live", "org.el.openglo.live.elazure"])
    with tempfile.TemporaryDirectory() as s:
        pkg(s, "wallpapers", "org.el.openglo.live", "org.el.openglo.live")
        tb = os.path.join(s, SHARE, "kwin", "tabbox", "org.el.taskswitch")
        os.makedirs(tb)
        with open(os.path.join(tb, "metadata.json"), "w") as fh:
            json.dump({"KPlugin": {"Id": "org.el.taskswitch"}}, fh)
        os.makedirs(os.path.join(s, "usr", "bin"))
        with open(os.path.join(s, "usr", "bin", "apply"), "w") as fh:
            fh.write('PID="org.el.openglo.$(echo "$V" | tr A-Z a-z)"\n')
        m = measure(s)
        chk("a kwin task switcher outside usr/share/plasma is SHIPPED",
            "org.el.taskswitch" in {x["id"] for x in m["shipped"]}, True)
        chk("an id completed at run time (`org.el.openglo.$(...)`) reads as a PREFIX",
            [(r["id"], r["prefix"]) for r in m["referenced"]], [("org.el.openglo", True)])
    chk("a tree with no usr/share/plasma is withheld, not empty-and-fine",
        measure(tempfile.gettempdir())["withheld"] is not None, True)
    print("check_plugin_ids selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    args = list(argv[1:])
    stage = None
    if "--stage" in args:
        i = args.index("--stage")
        if i + 1 >= len(args) or not os.path.isdir(args[i + 1]):
            print("check_plugin_ids: --stage needs an existing directory", file=sys.stderr)
            return 2
        stage = args[i + 1]
        del args[i:i + 2]
    for a in args:
        if a not in ("--json", "--list", "--selftest"):
            print(f"check_plugin_ids: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in args:
        return 0 if _selftest() else 1
    m = staged_measure(stage)
    if "--json" in args:
        print(json.dumps(m, indent=1))
        return 0
    if "--list" in args:
        shipped = {x["id"] for x in m["shipped"]}

        def found(rid, pre):
            return any(s.startswith(rid + ".") for s in shipped) if pre else rid in shipped
        refs = sorted({(r["id"], r["prefix"]) for r in m["referenced"]})
        for x in m["shipped"]:
            print(f"  shipped  {x['kind']:20} {x['dir']:40} {'' if x['dir_matches'] else 'ID=' + str(x['id'])}")
        for rid, pre in refs:
            print(f"  ref      {'shipped' if found(rid, pre) else 'DANGLING':9} {rid}{'.* (prefix)' if pre else ''}")
        print(f"check_plugin_ids: {sum(found(r, p) for r, p in refs)} of {len(refs)} referenced id(s) shipped; "
              f"{sum(x['dir_matches'] for x in m['shipped'])} of {len(m['shipped'])} package Id(s) match their directory")
        return 0
    print("usage: check_plugin_ids.py --json | --list | --selftest [--stage DIR]  (verdict: opa_gate plugin_ids)",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
