#!/usr/bin/env python3
"""check_atomic_writes.py — does every generator write its files ATOMICALLY?

⚑ WHY (W68, measured 2026-09-23). The pre-commit gate runs checks in parallel.
@EMITTERS runs make_schemes as __main__, which rewrote the TRACKED EL-*.colors
files with `open(f, "w").write(...)` — truncate, then write. Meanwhile CHROME,
FIREFOX and ~20 other importers of make_preview.parse_scheme READ those files. A
read in the gap sees an empty or half-written file and raises; on replay
@EMITTERS is not running, so the check passes: a flake. A race harness measured
truncate-then-write tearing 40114 of 200988 reads, and tempfile + os.replace 0.

So every write a generator makes goes through `emitters.atomic_write` (same-dir
mkstemp, write, mode from the umask, os.replace): a reader sees the old file or
the new one, never half of either.

    scripts/check_atomic_writes.py            # human report, n of m
    scripts/check_atomic_writes.py --json     # the measurement, for policy/atomic_writes.rego
    scripts/check_atomic_writes.py --selftest # the scan can SEE a plain open(..., "w")
    scripts/opa_gate.py atomic_writes         # the verdict

POPULATION: every module in emitters.ROLES (authorities, emitters, colourless
generators, the packager). A write site is: open()/io.open() with a mode holding
w, a, x or +; Path.write_text / write_bytes; shutil.copy / copy2 / copyfile /
copytree / move; the path-taking savers .save(<arg>) and .write_to_png(<arg>);
and cairosvg's svg2png(write_to=...). ADMITTED forms: a call to
emitters.atomic_write, and any of the above inside `with atomic_path(dst) as
tmp:` whose arguments name `tmp` (the helper's temp file, replaced onto dst).

EXEMPTION is declared AT THE SITE, never here: a comment
`# atomic-write: exempt — <reason>` on the site's line or the line above. The
reason is carried into the measurement and the policy refuses an empty one — a
write into a private tempdir, a selftest fixture, a staging DESTDIR nobody else
reads during a gate.

WEAKNESSES, stated: (1) STATIC. It sees call syntax, not targets: a write routed
through a local helper function is seen at the helper's open(), which is the
right place; a write through an API this scan does not name (e.g. a library
that takes a path and writes it itself, spelled other than .save/.write_to_png)
is invisible. (2) A non-literal mode argument is reported as mode "?" and
treated as a write — conservative, never silent. (3) `.save(` also matches
non-file saves; those are exempted at the site with their reason, which is
where a reader would look anyway. (4) It proves the SPELLING is atomic, not the
filesystem: os.replace is atomic within one filesystem, which a same-directory
mkstemp guarantees.
"""
import ast
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

EXEMPT_TAG = "atomic-write: exempt"
COPIERS = {"copy", "copy2", "copyfile", "copytree", "move"}
SAVERS = {"save", "write_to_png"}
HELPER = "atomic_write"
PATH_HELPER = "atomic_path"


def _mode(call):
    """The literal mode of an open() call, '?' if not literal, 'r' if absent."""
    arg = call.args[1] if len(call.args) > 1 else None
    for kw in call.keywords:
        if kw.arg == "mode":
            arg = kw.value
    if arg is None:
        return "r"
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    return "?"


def _exemption(lines, lineno):
    """The reason text of an exemption comment on this line or the one above."""
    for ln in (lineno, lineno - 1):
        if 1 <= ln <= len(lines):
            text = lines[ln - 1]
            i = text.find(EXEMPT_TAG)
            if i >= 0:
                return text[i + len(EXEMPT_TAG):].strip(" —-:\t") or ""
    return None


def _guarded(tree):
    """{id(call)} of every call inside a `with atomic_path(dst) as tmp:` body whose
    arguments NAME `tmp` — a path-taking writer aimed at the helper's temp file."""
    out = set()
    for w in ast.walk(tree):
        if not isinstance(w, ast.With):
            continue
        tmps = set()
        for item in w.items:
            c = item.context_expr
            fn = c.func if isinstance(c, ast.Call) else None
            nm = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else None
            if nm == PATH_HELPER and isinstance(item.optional_vars, ast.Name):
                tmps.add(item.optional_vars.id)
        if not tmps:
            continue
        for stmt in w.body:
            for n in ast.walk(stmt):
                if isinstance(n, ast.Call) and any(
                        isinstance(a, ast.Name) and a.id in tmps
                        for a in list(n.args) + [k.value for k in n.keywords]):
                    out.add(id(n))
    return out


def sites(source, module):
    """[{module, line, kind, mode, atomic, exempt, reason}] for every write site."""
    tree = ast.parse(source)
    lines = source.splitlines()
    guarded = _guarded(tree)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else None
        base = f.value.id if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) else None
        kind = mode = None
        if name == HELPER:
            kind = HELPER
        elif name == "svg2png" and any(k.arg == "write_to" for k in node.keywords):
            kind = "svg2png"
        elif name == "open" and (base is None or base == "io"):
            mode = _mode(node)
            if mode == "?" or any(c in mode for c in "wax+"):
                kind = "open"
        elif name in ("write_text", "write_bytes"):
            kind = name
        elif name in COPIERS and base == "shutil":
            kind = "shutil." + name
        elif name in SAVERS and node.args:
            kind = name
        if kind is None:
            continue
        ex = _exemption(lines, node.lineno)
        out.append({"module": module, "line": node.lineno, "kind": kind, "mode": mode,
                    "atomic": kind == HELPER or id(node) in guarded,
                    "exempt": ex is not None,
                    "reason": ex if ex is not None else None})
    return sorted(out, key=lambda s: s["line"])


def measure():
    """The --json document: the population and every write site in it."""
    import emitters
    modules = emitters.declared()
    cases, withheld = [], []
    for m in modules:
        path = os.path.join(ROOT, m + ".py")
        try:
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
        except OSError as e:
            withheld.append({"module": m, "withheld": f"unreadable: {e}"})
            continue
        cases.extend(sites(src, m))
    return {"modules": modules, "cases": cases, "unreadable": withheld,
            "helper": "emitters." + HELPER,
            "helper_present": callable(getattr(emitters, HELPER, None))}


def _selftest():
    """The scan SEES what it looks for: a plain open(..., 'w') is a write site
    and not atomic; the helper call is the atomic kind; a read is not a site; an
    exemption carries its reason; and the live helper really replaces."""
    import tempfile
    import emitters
    ok = True

    def see(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        ok = ok and cond

    fixture = (
        'open("EL-X.colors", "w").write("x")\n'
        'emitters.atomic_write("EL-Y.colors", "y")\n'
        'data = open("EL-Z.colors").read()\n'
        '# atomic-write: exempt — a private tempdir\n'
        'open(tmpname, "wb")\n'
        'pathlib.Path("q").write_text("z")\n'
        'shutil.copy2(a, b)\n'
        'img.save(dst)\n'
        'open(p, mode)\n'
        'with emitters.atomic_path(dst) as tmp:\n'
        '    img.save(tmp)\n'
        '    other.save(dst)\n'
        'cairosvg.svg2png(bytestring=b, write_to=dst)\n'
    )
    s = {x["line"]: x for x in sites(fixture, "fixture")}
    see("a plain open(..., 'w') is a non-atomic, non-exempt open site",
        s.get(1, {}).get("kind") == "open" and not s[1]["atomic"] and not s[1]["exempt"])
    see("the helper call is counted as atomic", s.get(2, {}).get("atomic") is True)
    see("a read-mode open is NOT a write site", 3 not in s)
    see("an exemption is seen, with its reason", s.get(5, {}).get("exempt") is True and s[5]["reason"] == "a private tempdir")
    see("Path.write_text is a write site", s.get(6, {}).get("kind") == "write_text")
    see("shutil.copy2 is a write site", s.get(7, {}).get("kind") == "shutil.copy2")
    see(".save(path) is a write site", s.get(8, {}).get("kind") == "save")
    see("a non-literal mode is conservatively a write", s.get(9, {}).get("mode") == "?")
    see("a saver aimed at atomic_path's temp is atomic", s.get(11, {}).get("atomic") is True)
    see("a saver in the same block aimed ELSEWHERE is not", s.get(12, {}).get("atomic") is False)
    see("svg2png(write_to=) is a write site", s.get(13, {}).get("kind") == "svg2png"
        and not s[13]["atomic"])
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "f.txt")
        emitters.atomic_write(p, "one")
        emitters.atomic_write(p, b"two")
        with open(p) as fh:
            body = fh.read()
        um = os.umask(0)
        os.umask(um)
        see("atomic_write writes text then bytes", body == "two")
        see("atomic_write leaves the umask mode, not mkstemp's 0600",
            os.stat(p).st_mode & 0o777 == 0o666 & ~um)
        see("atomic_write leaves no temp file behind", os.listdir(d) == ["f.txt"])
    doc = measure()
    see(f"the live population is non-empty ({len(doc['modules'])} modules, {len(doc['cases'])} sites)",
        len(doc["modules"]) > 0 and len(doc["cases"]) > 0)
    print("check_atomic_writes selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    known = {"--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_atomic_writes: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return _selftest()
    doc = measure()
    if "--json" in argv:
        print(json.dumps(doc, indent=1))
        return 0
    cases = doc["cases"]
    if not cases:
        print("check_atomic_writes: REFUSED — no write site found in "
              f"{len(doc['modules'])} module(s); the scan is broken", file=sys.stderr)
        return 1
    bad = [c for c in cases if not c["atomic"] and not c["exempt"]]
    for c in cases:
        tag = "atomic" if c["atomic"] else f"EXEMPT ({c['reason']})" if c["exempt"] else "PLAIN"
        print(f"  {c['module']}.py:{c['line']:<5d} {c['kind']:15s} {tag}")
    n_at = sum(c["atomic"] for c in cases)
    n_ex = sum(c["exempt"] for c in cases)
    print(f"\ncheck_atomic_writes: {n_at} atomic, {n_ex} exempt, {len(bad)} plain "
          f"of {len(cases)} write site(s) in {len(doc['modules'])} module(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
