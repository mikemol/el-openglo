#!/usr/bin/env python3
"""check_modes — run every declared mode of every check (W67).

A warrant cites ONE invocation of a check, so a mode nobody cites (a broken
`--list`) stays green forever. But every `scripts/check_*.py` already DECLARES
its modes: the `known = {...}` set it uses to refuse unknown flags. This tool
reads that set by AST (never by regex), runs each read-only mode as a
subprocess, and reports which ones do not RUN.

A mode FAILS when it raises (a "Traceback" on stderr) or exits 2 — the
unknown-flag refusal, i.e. the declared set disagrees with the parser. Exit 1
(denied) and 3 (withheld) are legitimate verdicts about the tree, not failures
of the mode. A timeout is reported separately as UNMEASURED, not failed.

Excluded by DECLARATION (the EXCLUDE table below, each with its reason), never
by pattern-matching flag names. A flag the script reads an argument for
(`argv.index(flag)` / `args.index(flag)` in its source) cannot be run bare and
is reported SKIPPED, counted.

WEAKNESS: this proves a mode RUNS — terminates without a traceback and without
refusing its own declared flag. It never proves the mode's OUTPUT is right, and
a mode that swallows its exception and exits 0 passes. It also only sees checks
that declare `known` as a literal; a check without one is reported, not run.

    check_modes.py            run and report
    check_modes.py --list     the discovered mode table, no execution
    check_modes.py --json     the measurement
    check_modes.py --selftest prove a raising mode is seen, and 0-of-0 refuses
"""
import ast
import json
import os
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
SELF = os.path.basename(__file__)
TIMEOUT = 300.0

# EXCLUDE BY DECLARATION. Each flag here is not read-only (or would recurse),
# and says why. Add a row when a new mutating mode is declared; never infer.
EXCLUDE = {
    # asserts a build: records keys/manifests saying outputs were built
    "--write": "mutates: records state asserting a build happened",
    # mutate the tree
    "--fix": "mutates: rewrites files in place",
    "--apply": "mutates: applies a change to the tree",
    # every check's selftest is run by run_selftests.py; here it would recurse
    # (this tool's own) and double the slowest part of the gate
    "--selftest": "covered by run_selftests.py; recursive and slow here",
    # per-check rows, read from each main() before admitting the mode:
    ("check_template_parity.py", "--unlink"):
        "mutates: rewrites catalog/baselines/* to give each its own inode",
    ("check_template_parity.py", "--record"):
        "mutates: re-records ONE baseline from the tree's emission",
    ("check_publishing.py", "--refresh"):
        "mutates + network: fetches the OCS listing and overwrites the cache",
    ("check_font.py", "--render"):
        "mutates: writes glyph.png into the working directory",
}

# Arguments read positionally (not by .index), which the AST scan cannot see.
# Declared, per check, from reading its main().
POSITIONAL = {
    ("check_template_parity.py", "--diff"):
        "needs a pair name as a positional operand; bare exits 2 by design",
    ("check_display_registry.py", "--glyph"):
        "needs a character as a positional operand; bare exits 2 by design",
    ("check_symbol.py", "--bucket"):
        "needs exactly one bucket name as a positional operand; bare exits 2",
}


def excluded(check, flag):
    return EXCLUDE.get((check, flag)) or EXCLUDE.get(flag)


def declared_known(path):
    """The `known` literal in `path`, found by AST at any depth, or None."""
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(t, ast.Name) and t.id == "known" for t in node.targets):
            continue
        if isinstance(node.value, (ast.Set, ast.List, ast.Tuple)):
            elts = node.value.elts
            if all(isinstance(e, ast.Constant) and isinstance(e.value, str)
                   for e in elts):
                return sorted(e.value for e in elts), tree
    return None, tree


def arg_taking(tree):
    """Flags the source reads an argument for: `<x>.index("--flag")` calls."""
    out = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "index" and len(node.args) == 1
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
                and node.args[0].value.startswith("-")):
            out.add(node.args[0].value)
    return out


def discover(scripts_dir, exclude=SELF):
    """Per check: its declared modes, each classified run / excluded / skipped."""
    checks = []
    for name in sorted(os.listdir(scripts_dir)):
        if not (name.startswith("check_") and name.endswith(".py")) or name == exclude:
            continue
        path = os.path.join(scripts_dir, name)
        known, tree = declared_known(path)
        rec = {"check": name, "path": path, "declares_known": known is not None,
               "modes": []}
        if known is not None:
            takes = arg_taking(tree)
            for flag in known:
                if excluded(name, flag):
                    rec["modes"].append({"mode": flag, "plan": "excluded",
                                         "reason": excluded(name, flag)})
                elif (name, flag) in POSITIONAL:
                    rec["modes"].append({"mode": flag, "plan": "skipped",
                                         "reason": POSITIONAL[(name, flag)]})
                elif flag in takes:
                    rec["modes"].append({"mode": flag, "plan": "skipped",
                                         "reason": "takes an argument (.index(flag))"})
                else:
                    rec["modes"].append({"mode": flag, "plan": "run"})
        checks.append(rec)
    return checks


def run_mode(path, mode, cwd, timeout=TIMEOUT):
    """Run one mode; per-child CPU from wait4, wall from the clock."""
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
        t0 = time.monotonic()
        p = subprocess.Popen([sys.executable, path, mode], cwd=cwd,
                             stdin=subprocess.DEVNULL, stdout=out, stderr=err)
        while True:
            pid, status, ru = os.wait4(p.pid, os.WNOHANG)
            if pid:
                break
            if time.monotonic() - t0 > timeout:
                p.kill()
                pid, status, ru = os.wait4(p.pid, 0)
                p.returncode = -9
                return {"exit": None, "timeout": True, "traceback": False,
                        "wall_s": round(time.monotonic() - t0, 2),
                        "cpu_s": round(ru.ru_utime + ru.ru_stime, 2)}
            time.sleep(0.05)
        p.returncode = os.waitstatus_to_exitcode(status)
        wall = time.monotonic() - t0
        err.seek(0)
        stderr = err.read().decode("utf-8", "replace")
    tb = "Traceback" in stderr
    return {"exit": p.returncode, "timeout": False, "traceback": tb,
            "wall_s": round(wall, 2), "cpu_s": round(ru.ru_utime + ru.ru_stime, 2),
            "stderr_tail": stderr.strip().splitlines()[-1] if (tb or p.returncode == 2)
            and stderr.strip() else ""}


def verdict(r):
    if r["timeout"]:
        return "timeout"
    if r["traceback"]:
        return "FAIL-traceback"
    if r["exit"] == 2:
        return "FAIL-exit2"
    return "ok"


def measure(scripts_dir=SCRIPTS, cwd=ROOT, exclude=SELF, jobs=4, timeout=TIMEOUT):
    checks = discover(scripts_dir, exclude)
    todo = [(c, m) for c in checks for m in c["modes"] if m["plan"] == "run"]
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        results = list(ex.map(lambda cm: run_mode(cm[0]["path"], cm[1]["mode"],
                                                   cwd, timeout), todo))
    for (c, m), r in zip(todo, results):
        m.update(r)
        m["verdict"] = verdict(r)
    for c in checks:
        c.pop("path")
    return {"checks": checks}


def summarize(m):
    checks = m["checks"]
    modes = [x for c in checks for x in c["modes"]]
    ran = [x for x in modes if x["plan"] == "run"]
    return {
        "K": len(checks),
        "k_declaring": sum(c["declares_known"] for c in checks),
        "m_declared": len(modes),
        "ran": len(ran),
        "clean": sum(x["verdict"] == "ok" for x in ran),
        "failed": [(c["check"], x) for c in checks for x in c["modes"]
                   if x.get("verdict", "").startswith("FAIL")],
        "timeout": [(c["check"], x) for c in checks for x in c["modes"]
                    if x.get("verdict") == "timeout"],
        "skipped": sum(x["plan"] == "skipped" for x in modes),
        "excluded": sum(x["plan"] == "excluded" for x in modes),
    }


def report(m):
    s = summarize(m)
    if s["ran"] == 0:
        print("check_modes: REFUSED — 0 runnable modes discovered; the search is "
              "broken, not the tree clean", file=sys.stderr)
        return 2
    for c in m["checks"]:
        if not c["declares_known"]:
            print(f"  {c['check']:32s} ⚑ declares no `known` literal — not run")
            continue
        for x in c["modes"]:
            if x["plan"] != "run":
                print(f"  {c['check']:32s} {x['mode']:18s} {x['plan']:9s} ({x['reason']})")
            else:
                print(f"  {c['check']:32s} {x['mode']:18s} {x['verdict']:15s} "
                      f"exit={x['exit']} wall={x['wall_s']}s cpu={x['cpu_s']}s")
    for name, x in s["failed"]:
        print(f"  ⚑ FAILED {name} {x['mode']}: {x['stderr_tail']}", file=sys.stderr)
    for name, x in s["timeout"]:
        print(f"  UNMEASURED {name} {x['mode']}: timed out", file=sys.stderr)
    print(f"\ncheck_modes: {s['clean']} of {s['ran']} run mode(s) clean across "
          f"{s['k_declaring']} of {s['K']} check(s) declaring `known`; "
          f"{len(s['failed'])} failed, {len(s['timeout'])} timed out, "
          f"{s['skipped']} skipped (take an argument), {s['excluded']} excluded "
          f"(of {s['m_declared']} declared)")
    return 1 if s["failed"] else 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {'ok ' if good else 'BAD'} {label}: got {got!r}, want {want!r}")

    with tempfile.TemporaryDirectory() as d:
        src = (
            "import sys\n"
            "def main(argv):\n"
            "    known = {'--good', '--boom', '--nodecl', '--name', '--write'}\n"
            "    if '--name' in argv: print(argv[argv.index('--name') + 1])\n"
            "    if '--boom' in argv: raise RuntimeError('seen')\n"
            "    if '--nodecl' in argv: return 2\n"
            "    return 0\n"
            "sys.exit(main(sys.argv))\n")
        with open(os.path.join(d, "check_fake.py"), "w") as f:
            f.write(src)
        m = measure(d, d, exclude=None, jobs=2, timeout=30)
        modes = {x["mode"]: x for x in m["checks"][0]["modes"]}
        chk("raising mode is FAIL-traceback", modes["--boom"]["verdict"], "FAIL-traceback")
        chk("exit-2 mode is FAIL-exit2", modes["--nodecl"]["verdict"], "FAIL-exit2")
        chk("clean mode is ok", modes["--good"]["verdict"], "ok")
        chk("argument-taking mode skipped", modes["--name"]["plan"], "skipped")
        chk("--write excluded by declaration", modes["--write"]["plan"], "excluded")
        chk("failures make report exit 1", report(m), 1)
    with tempfile.TemporaryDirectory() as d:
        chk("empty population refuses", report(measure(d, d, exclude=None)), 2)
    print("check_modes selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    known = {"--list", "--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_modes: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return _selftest()
    if "--list" in argv:
        checks = discover(SCRIPTS)
        n = 0
        for c in checks:
            if not c["declares_known"]:
                print(f"  {c['check']:32s} ⚑ declares no `known` literal")
            for x in c["modes"]:
                n += 1
                print(f"  {c['check']:32s} {x['mode']:18s} {x['plan']}"
                      + (f"  ({x['reason']})" if "reason" in x else ""))
        print(f"\ncheck_modes: {n} declared mode(s) over {len(checks)} check(s)")
        return 0 if n else 2
    m = measure()
    if "--json" in argv:
        print(json.dumps(m, indent=1))
        return 0 if summarize(m)["ran"] else 2
    return report(m)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
