#!/usr/bin/env python3
"""check_rego_lint.py — the policies' own hazards, read from opa's AST (never the text).

⚑ WHY (2026-09-23, Rego batch 5). Two rego traps a policy author walks into, each
invisible until the rule fires on the input nobody rendered:

  truthy  — REGO NULL IS TRUTHY. An expression that is only a reference
            (`input.withheld`, `c.recursive`) SUCCEEDS whenever the value is
            DEFINED and not `false`: null, "", 0, [] and {} all fire it. An
            unrecognised or null field then fires a rule meant for a real value.
            Batch 5's drafts had this bug and their own tests caught it; the
            older policies had never been checked.
  fixed   — sprintf's %.Nf / %f / %e / %g print an integral JSON number (25.0
            arrives as the int 25) as "%!f(int=25)" — in exactly the deny message
            nobody has seen rendered. policy/lib/fmt.rego's fixed(x, n) is the
            formatter that prints both alike.

    scripts/check_rego_lint.py            # human report, n of m
    scripts/check_rego_lint.py --json     # the measurement, for policy/rego_lint.rego
    scripts/check_rego_lint.py --selftest # the scan SEES both kinds on a fixture
    scripts/check_rego_lint.py --fix      # wrap each bare VALUE reference as truth.py(<ref>)
                                          # (policy/lib/truth.rego: Python's bool(), the
                                          # meaning a --json measurement's author had)
    scripts/opa_gate.py rego_lint         # the verdict

POPULATION: the tracked policy/**.rego (scripts/git_tracked.py), tests included —
a test that asserts through a bare reference is as exposed as a rule. Each file is
parsed by `opa parse --format json --json-include locations`.

A TRUTHY site is an expression, in ANY body (rule, else, function, comprehension,
`every`), whose terms are ONE term of type `ref` or `var`, not negated. Its `root` is the
reference's head variable, classified:
  input  — the head is `input`;
  local  — a variable the module does not define as a rule or import (a `some`
           binding, an iteration var, a function argument);
  rule   — the head is a rule of this module, an import alias, or `data`.
`input` and `local` are VALUES and the finding; a `rule` reference names a rule
whose own body decides when it is defined, and is recorded, not judged.

A FIXED site is a call to sprintf whose format (a string literal) holds a
floating-point verb: %f %F %e %E %g %G, with any flags / width / precision.

A NEGATED site is `not <dotted value ref>` (`not c.withheld`): `not null` is FALSE,
so a null field reads as PRESENT — root_helpers' `runs` and cursors' `measured`
dropped every case whose `withheld` was null. It has no --fix: whether null
means "falsy" (`not truth.py(object.get(c, "withheld", null))`) or "not measured"
(a withheld message, `c.present == false` for the deny) is the policy's call,
and each policy's all-null test is what settles it.

WEAKNESSES, stated: (1) a `rule` reference to a rule whose VALUE can be null
(`x := input.maybe`) is the same trap one hop away, and is not flagged. (2) A
`not` over a lone var (`not x`) is not flagged: it is nearly always a rule. (3) A sprintf whose format is
not a literal is invisible. (4) opa absent is a SKIP (withheld), not a clean tree.
"""
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import git_tracked  # noqa: E402

OPA = shutil.which("opa")
SCOPE = ("policy/*.rego",)
FLOAT_VERB = re.compile(r"%[-+ #0]*\d*(?:\.\d+)?[fFeEgG]")


def parse(path, opa=None):
    """opa's JSON AST of one file (with locations)."""
    r = subprocess.run([opa or OPA, "parse", "--format", "json", "--json-include", "locations", path],
                       capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise ValueError(r.stderr.strip()[-300:])
    return json.loads(r.stdout)


def _text(node):
    loc = node.get("location") or {}
    t = loc.get("text")
    try:
        return base64.b64decode(t).decode("utf-8") if t else ""
    except (ValueError, UnicodeDecodeError):
        return ""


def _row(node):
    return (node.get("location") or {}).get("row", 0)


def _defined(ast):
    """Names a bare reference may legitimately head: rule names, import aliases, data."""
    names = {"data"}
    for r in ast.get("rules", []):
        head = r.get("head", {})
        if head.get("name"):
            names.add(head["name"])
        ref = head.get("ref") or []
        if ref and ref[0].get("type") == "var":
            names.add(ref[0]["value"])
    for imp in ast.get("imports", []):
        if imp.get("alias"):
            names.add(imp["alias"])
        path = (imp.get("path") or {}).get("value") or []
        if path:
            names.add(path[-1].get("value"))
    return names


def _exprs(node):
    """Every expression in every body, at any depth."""
    if isinstance(node, dict):
        if "terms" in node and "index" in node:
            yield node
        for v in node.values():
            yield from _exprs(v)
    elif isinstance(node, list):
        for v in node:
            yield from _exprs(v)


def _calls(node):
    """Every call term, at any depth, as (node, [operator term, args...])."""
    if isinstance(node, dict):
        if node.get("type") == "call" and isinstance(node.get("value"), list):
            yield node, node["value"]
        for v in node.values():
            yield from _calls(v)
    elif isinstance(node, list):
        for v in node:
            yield from _calls(v)


def _op(term):
    if term.get("type") == "ref":
        return ".".join(str(p.get("value")) for p in term["value"])
    return None


def sites(ast, module):
    """{'truthy': [...], 'fixed': [...]} for one parsed module."""
    defined = _defined(ast)
    truthy, fixed, negated = [], [], []
    for e in _exprs(ast.get("rules", [])):
        t = e["terms"]
        # a lone name (`helper`, `x`) parses as a `var` term, a dotted one as a `ref`
        if isinstance(t, dict) and t.get("type") in ("ref", "var"):
            head = t["value"][0] if t["type"] == "ref" else t
            name = head.get("value") if head.get("type") == "var" else None
            root = "input" if name == "input" else "rule" if name in defined else "local"
            if e.get("negated"):
                # `not c.x` with c.x == null is FALSE: null reads as present. Only a
                # dotted VALUE ref is a site — `not helper` negates a rule.
                if t["type"] == "ref" and root != "rule":
                    negated.append({"module": module, "line": _row(t) or _row(e), "root": root,
                                    "col": (t.get("location") or {}).get("col", 0),
                                    "text": _text(t), "value": True})
                continue
            truthy.append({"module": module, "line": _row(e) or _row(t), "root": root,
                           "col": (e.get("location") or t.get("location") or {}).get("col", 0),
                           "text": _text(e) or _text(t), "value": root != "rule"})
    # an infix call (`x == y`) is an expression whose terms are a LIST; sprintf is
    # always a call term, so the call walk sees it inside any body or head
    for node, parts in _calls(ast.get("rules", [])):
        if _op(parts[0]) != "sprintf" or len(parts) < 2:
            continue
        f = parts[1]
        if f.get("type") == "string" and FLOAT_VERB.search(f["value"]):
            fixed.append({"module": module, "line": _row(node) or _row(f), "format": f["value"],
                          "verbs": FLOAT_VERB.findall(f["value"])})
    for e in _exprs(ast.get("rules", [])):
        t = e["terms"]
        if isinstance(t, list) and t and _op(t[0]) == "sprintf" and len(t) > 1:
            f = t[1]
            if f.get("type") == "string" and FLOAT_VERB.search(f["value"]):
                fixed.append({"module": module, "line": _row(e), "format": f["value"],
                              "verbs": FLOAT_VERB.findall(f["value"])})
    return {"truthy": sorted(truthy, key=lambda s: s["line"]),
            "negated": sorted(negated, key=lambda s: s["line"]),
            "fixed": sorted(fixed, key=lambda s: s["line"])}


def measure(root=ROOT, opa=None):
    opa = OPA if opa is None else opa
    files = git_tracked.files(*SCOPE, root=root)
    doc = {"scope": list(SCOPE), "files": files, "truthy": [], "negated": [], "fixed": [], "unreadable": []}
    if not opa:
        doc["unreadable"] = [{"module": f, "withheld": "opa is not installed on this host"} for f in files]
        return doc
    for rel in files:
        try:
            s = sites(parse(os.path.join(root, rel), opa), rel)
        except (ValueError, OSError, json.JSONDecodeError, subprocess.SubprocessError) as e:
            doc["unreadable"].append({"module": rel, "withheld": f"unparsed: {e}"})
            continue
        doc["truthy"].extend(s["truthy"])
        doc["negated"].extend(s["negated"])
        doc["fixed"].extend(s["fixed"])
    return doc


IMPORT = "import data.el.truth"


def rewrite(source, sites_):
    """`source` with each bare VALUE reference in `sites_` wrapped as truth.py(<ref>),
    and `import data.el.truth` added after `import rego.v1` when absent. A site
    whose text is not found at its (line, col) is left alone and returned in the
    `skipped` list — never guessed at."""
    lines = source.split("\n")
    skipped = []
    for s in sorted(sites_, key=lambda s: (s["line"], s["col"]), reverse=True):
        i, c, t = s["line"] - 1, s["col"] - 1, s["text"]
        if not (0 <= i < len(lines)) or lines[i][c:c + len(t)] != t:
            skipped.append(s)
            continue
        lines[i] = lines[i][:c] + f"truth.py({t})" + lines[i][c + len(t):]
    if len(skipped) < len(sites_) and IMPORT not in lines:
        # after `import rego.v1`, else after the package clause (a v1-only module)
        at = lines.index("import rego.v1") + 1 if "import rego.v1" in lines else next(
            (i + 1 for i, ln in enumerate(lines) if ln.startswith("package ")), None)
        if at is None:
            return source, list(sites_)
        lines[at:at] = ["", IMPORT]
    return "\n".join(lines), skipped


def fix(root=ROOT):
    """--fix: apply rewrite() to every file with a T1 finding. Returns (n fixed, skipped)."""
    doc = measure(root)
    by = {}
    for s in doc["truthy"]:
        if s["value"]:
            by.setdefault(s["module"], []).append(s)
    n, skipped = 0, []
    for rel, ss in sorted(by.items()):
        path = os.path.join(root, rel)
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        out, sk = rewrite(src, ss)
        skipped.extend(sk)
        n += len(ss) - len(sk)
        if out != src:
            fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".rego_lint.")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(out)
            os.chmod(tmp, os.stat(path).st_mode & 0o777)
            os.replace(tmp, path)
    return n, skipped


FIXTURE = """package el.fixture

import rego.v1

import data.el.other

deny contains msg if {
	some c in input.cases
	c.flag
	not c.other
	c.n == 0
	msg := sprintf("%s %.2f %d", [c.name, c.x, c.n])
}

deny contains "w" if input.withheld

deny contains "r" if helper

deny contains "o" if other.deny

helper if count([x | some x in input.xs; x.on]) > 0

nothelper if not helper

cmp if input.withheld == true
"""


def _selftest():
    ok = True

    def see(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        ok = ok and cond

    see("a float verb is seen with flags and precision",
        [bool(FLOAT_VERB.search(s)) for s in ("%.2f", "%5.1f", "%f", "%g", "%d", "%s", "%%d")]
        == [True, True, True, True, False, False, False])
    if not OPA:
        print("  SKIP — opa absent: the AST arms cannot run on this host")
        print("check_rego_lint selftest: SKIP")
        return 0
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "fixture.rego")
        with open(p, "w") as fh:  # atomic-write: exempt — private fixture tempdir
            fh.write(FIXTURE)
        s = sites(parse(p), "fixture.rego")
    by = {x["text"]: x for x in s["truthy"]}
    see(f"a bare local reference is a VALUE site ({sorted(by)})",
        by.get("c.flag", {}).get("root") == "local" and by["c.flag"]["value"])
    see("a bare input reference in a one-line rule is an input site",
        by.get("input.withheld", {}).get("root") == "input")
    see("a bare reference inside a comprehension body is seen", by.get("x.on", {}).get("root") == "local")
    see("a negated reference is not a TRUTHY site", "c.other" not in by)
    neg = {x["text"]: x for x in s["negated"]}
    see(f"a negated value reference IS a negated site ({sorted(neg)})",
        neg.get("c.other", {}).get("root") == "local" and neg["c.other"]["line"] == 10)
    see("`not <rule>` is not a negated site", "helper" not in neg and len(neg) == 1)
    see("a comparison is not a site", not any("==" in t for t in by))
    see("a rule reference and an import-alias reference are `rule`, not values",
        by.get("helper", {}).get("value") is False and by.get("other.deny", {}).get("value") is False)
    see(f"the %.2f sprintf is a fixed site ({[f['verbs'] for f in s['fixed']]})",
        len(s["fixed"]) == 1 and s["fixed"][0]["verbs"] == ["%.2f"] and s["fixed"][0]["line"] == 12)
    vals = [x for x in s["truthy"] if x["value"]]
    out, sk = rewrite(FIXTURE, vals)
    see(f"--fix wraps every value site and imports truth once ({len(sk)} skipped)",
        not sk and "\ttruth.py(c.flag)\n" in out and "truth.py(input.withheld)" in out
        and "\thelper\n" not in out and out.count(IMPORT) == 1 and "not c.other" in out)
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "fixed.rego")
        with open(p, "w") as fh:  # atomic-write: exempt — private fixture tempdir
            fh.write(out)
        again = sites(parse(p), "fixed.rego")
    see("the rewritten fixture parses and has no value site left",
        not [x for x in again["truthy"] if x["value"]])
    doc = measure()
    see(f"the live population is non-empty ({len(doc['files'])} files, {len(doc['unreadable'])} unparsed)",
        len(doc["files"]) > 0 and not doc["unreadable"])
    print("check_rego_lint selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    known = {"--json", "--selftest", "--fix"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_rego_lint: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return _selftest()
    if "--fix" in argv:
        if not OPA:
            print("check_rego_lint: SKIP — opa is not installed on this host", file=sys.stderr)
            return 0
        n, skipped = fix()
        for s in skipped:
            print(f"  SKIPPED {s['module']}:{s['line']}:{s['col']} `{s['text']}` — not found at its location")
        print(f"check_rego_lint --fix: {n} of {n + len(skipped)} bare value reference(s) wrapped in truth.py")
        return 1 if skipped else 0
    doc = measure()
    if "--json" in argv:
        print(json.dumps(doc, indent=1))
        return 0
    if not doc["files"]:
        print("check_rego_lint: REFUSED — no policy file in scope; the search is broken", file=sys.stderr)
        return 1
    vals = [t for t in doc["truthy"] if t["value"]]
    for t in doc["truthy"]:
        print(f"  truthy {t['module']}:{t['line']:<4d} {t['root']:6s} {t['text']}")
    for t in doc["negated"]:
        print(f"  negated {t['module']}:{t['line']:<4d} {t['root']:6s} not {t['text']}")
    for f in doc["fixed"]:
        print(f"  fixed  {f['module']}:{f['line']:<4d} {' '.join(f['verbs'])}  {f['format'][:60]}")
    for u in doc["unreadable"]:
        print(f"  SKIP {u['module']}: {u['withheld']}")
    print(f"\ncheck_rego_lint: {len(vals)} bare VALUE reference(s) of {len(doc['truthy'])} bare "
          f"reference(s), {len(doc['negated'])} negated value reference(s), "
          f"{len(doc['fixed'])} float-verb sprintf(s), over "
          f"{len(doc['files']) - len(doc['unreadable'])} of {len(doc['files'])} policy file(s) parsed")
    return 1 if vals or doc["negated"] or doc["fixed"] or doc["unreadable"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
