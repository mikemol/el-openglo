#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""typing_census.py — the house-strict mypy findings of this repo, per file and per idiom (W672 and W670, under W553)

The debt cards ("el-openglo typing: FILE (N findings)") were minted by the host's typing kata
(/home/mikemol/github/.claude/katas/katas.py), whose measure() REFUSES this repo: [tool.mypy] puts `scripts` and
`templates` on mypy_path with explicit_package_bases, each directory holds an `__init__.py`, and mypy resolves each
marker against its own directory as the base, so both become a top-level module named `__main__` ("Duplicate
module named __main__"). The kata's retry names the clashing FILE (templates/__init__.py) but its targets are
DIRECTORIES (templates), so the retry never separates them. This script reuses the kata's own functions
(mypy_targets, house_mypy, count_errors, EXCL_RE) and runs each package target in a pass of its own, the loose
files together, merging by the MAX count per file as the kata does. IT RETIRES when the graduated kata carries the
fix (mtools, via github-8f).

    scripts/typing_census.py             # findings per file (largest first), then n of m files and the total
    scripts/typing_census.py --codes     # the same findings per mypy error code and per idiom (message shape)
    scripts/typing_census.py --by-file-idiom   # per file: count, dominant code, its count, its idiom (the W676 plan)
    scripts/typing_census.py --json      # {files, codes, passes, withheld}
    scripts/typing_census.py --findings FILE   # one file's findings: path:line:col, code, message (W743)
    scripts/typing_census.py --selftest

⚑ WEAKNESS, STATED. It measures with the kata's flags, so it is exactly as strict as the kata; it is an interim
for the kata's defect, not a second definition of "house strict". A pass mypy cannot run (rc not 0 or 1) is
WITHHELD with its target and tail, never read as zero findings. A finding several passes report is counted once
for the idiom view (by file, line, column, code and message); the per-file view keeps the kata's MAX rule.
"""

import importlib.util
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KATAS = "/home/mikemol/github/.claude/katas/katas.py"
QUOTED = re.compile(r'"[^"]*"')
TOP_IDIOMS = 25


def load_katas(path=KATAS):
    """The kata module, loaded by path (it is a host script, not a package)."""
    spec = importlib.util.spec_from_file_location("katas", path)
    if spec is None or spec.loader is None:
        msg = f"cannot load {path}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def passes_of(targets):
    """Each package directory in a pass of its own; every loose file together: [[target, ...], ...]."""
    packages = [t for t in targets if not t.endswith(".py") and t != "."]
    loose = [t for t in targets if t.endswith(".py") or t == "."]
    return [[p] for p in packages] + ([loose] if loose else [])


def idiom(message):
    """A message with its quoted names taken out, so the same finding on different names counts together."""
    return QUOTED.sub('"…"', message)


def records_of(stdout, root):
    """The distinct findings of one mypy -O json output: (file, line, column, code, message) for files in `root`."""
    out = set()
    for line in stdout.splitlines():
        if not line.startswith("{"):
            continue
        rec = json.loads(line)
        path = str(rec.get("file", ""))
        if path.startswith(".") or not (Path(root) / path).exists():
            continue
        key = (
            path,
            rec.get("line"),
            rec.get("column"),
            rec.get("code") or "none",
            str(rec.get("message", "")),
        )
        out.add(key)
    return out


def census(root=ROOT, katas=None):
    """(files, withheld, npasses, records): findings per file merged by MAX over the passes, the passes mypy could
    not run (each {targets, rc, tail}), and the distinct findings across passes."""
    k = load_katas() if katas is None else katas
    args = ("-O", "json", "--exclude", k.EXCL_RE)
    files, withheld, records = {}, [], set()
    groups = passes_of(k.mypy_targets(root))
    for group in groups:
        done = k.house_mypy(root, group, *args)
        if done.returncode not in (0, 1):
            tail = (done.stdout + done.stderr).strip().splitlines()[-3:]
            withheld.append({"targets": group, "rc": done.returncode, "tail": tail})
            continue
        for path, n in k.count_errors(done.stdout, root).items():
            files[path] = max(files.get(path, 0), n)
        records |= records_of(done.stdout, root)
    return files, withheld, len(groups), records


def by_code(records):
    return Counter(r[3] for r in records)


def by_idiom(records):
    return Counter((r[3], idiom(r[4])) for r in records)


def by_file_idiom(records):
    """{file: {count, code, idiom, idiom_count}}: each file's distinct findings and the idiom that dominates it
    (ties go to the smaller code then message, so the plan is the same on every run)."""
    per = {}
    for path, _line, _col, code, message in records:
        per.setdefault(path, Counter())[(code, idiom(message))] += 1
    out = {}
    for path, counts in per.items():
        (code, shape), top = min(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        out[path] = {
            "count": sum(counts.values()),
            "code": code,
            "idiom": shape,
            "idiom_count": top,
        }
    return out


UNTYPED_CALLEE = re.compile(r'Call to untyped function "([^"]+)" in typed context')


def callees_of(records):
    """Counter of the untyped function NAMES the no-untyped-call findings name: the hub finder (W743).
    One signature on a name that many files call clears all of its findings at once."""
    out = Counter()
    for _file, _line, _col, code, message in records:
        m = UNTYPED_CALLEE.match(message) if code == "no-untyped-call" else None
        if m:
            out[m.group(1)] += 1
    return out


def findings_of(records, path):
    """The distinct findings of one file, in line order: [(line, column, code, message)]."""
    return sorted(
        (line, col, code, message)
        for file, line, col, code, message in records
        if file == path
    )


def main(argv):
    args = argv[1:]
    if args[:1] == ["--findings"] and len(args) == 2:
        _files, withheld, _n, records = census()
        rows = findings_of(records, args[1])
        for line, col, code, message in rows:
            print(f"{args[1]}:{line}:{col}\t{code}\t{message}")
        print(
            f"typing_census: {len(rows)} finding(s) in {args[1]}; {len(withheld)} pass(es) withheld",
            file=sys.stderr,
        )
        return 3 if withheld else 0
    if args == ["--callees"]:
        _files, withheld, _n, records = census()
        ranked = callees_of(records).most_common()
        for name, count in ranked:
            print(f"{count}\t{name}")
        print(
            f"typing_census: {len(ranked)} untyped callee name(s) cause {sum(c for _n, c in ranked)} finding(s); {len(withheld)} pass(es) withheld",
            file=sys.stderr,
        )
        return 3 if withheld else 0
    if args not in ([], ["--json"], ["--codes"], ["--by-file-idiom"]):
        print(f"typing_census: unknown arguments {args!r}", file=sys.stderr)
        return 2
    files, withheld, n, records = census()
    if args == ["--by-file-idiom"]:
        plan = by_file_idiom(records)
        for path, row in sorted(plan.items(), key=lambda kv: (-kv[1]["count"], kv[0])):
            print(
                f"{row['count']}\t{path}\t{row['code']}\t{row['idiom_count']}\t{row['idiom']}"
            )
    elif args == ["--json"]:
        out = {
            "files": files,
            "codes": dict(by_code(records)),
            "passes": n,
            "withheld": withheld,
        }
        print(json.dumps(out, indent=1))
    elif args == ["--codes"]:
        for code, count in by_code(records).most_common():
            print(f"code\t{count}\t{code}")
        for (code, shape), count in by_idiom(records).most_common(TOP_IDIOMS):
            print(f"idiom\t{count}\t{code}\t{shape}")
    else:
        for path, count in sorted(files.items(), key=lambda kv: (-kv[1], kv[0])):
            print(f"{count}\t{path}")
    print(
        f"typing_census: {len(files)} file(s) with findings, {sum(files.values())} finding(s) in {n} pass(es), "
        f"{len(records)} distinct; {len(withheld)} pass(es) withheld",
        file=sys.stderr,
    )
    return 3 if withheld else 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    chk(
        "each package gets a pass of its own and the loose files share one",
        passes_of(["scripts", "templates", "a.py", "b.py"]),
        [["scripts"], ["templates"], ["a.py", "b.py"]],
    )
    chk("no loose file means no loose pass", passes_of(["scripts"]), [["scripts"]])
    chk(
        "an idiom is the message with its quoted names taken out",
        idiom('Call to untyped function "project" in typed context'),
        'Call to untyped function "…" in typed context',
    )

    def rec(file, line, code, message):
        return json.dumps(
            {"file": file, "line": line, "column": 0, "code": code, "message": message}
        )

    class Done:
        def __init__(self, rc, out=""):
            self.returncode, self.stdout, self.stderr = rc, out, ""

    here = str(ROOT / "scripts" / "typing_census.py")
    rel = os.path.relpath(here, ROOT)
    same = rec(rel, 3, "misc", 'Expression has type "Any"')
    outputs = {
        "scripts": Done(
            1,
            same
            + "\n"
            + rec(rel, 9, "no-untyped-def", "Function is missing a type annotation"),
        ),
        "templates": Done(2, "boom"),
        "a.py": Done(1, same),
    }

    class Fake:
        EXCL_RE = "x"

        @staticmethod
        def mypy_targets(_root):
            return ["scripts", "templates", "a.py"]

        @staticmethod
        def house_mypy(_root, group, *_args):
            return outputs[group[0]]

        @staticmethod
        def count_errors(out, _root):
            return {rel: len([x for x in out.splitlines() if x.startswith("{")])}

    files, withheld, n, records = census(ROOT, Fake)
    chk("findings merge by the max over the passes that saw a file", files, {rel: 2})
    chk(
        "a pass mypy cannot run is withheld with its target, never read as zero",
        [w["targets"] for w in withheld],
        [["templates"]],
    )
    chk("n of m: three passes ran", n, 3)
    chk("a finding two passes both report is one distinct finding", len(records), 2)
    chk(
        "the idiom view counts per code and message shape",
        by_code(records),
        Counter({"misc": 1, "no-untyped-def": 1}),
    )
    plan = by_file_idiom(records)
    chk(
        "a file's dominant idiom is its most frequent (code, shape), ties to the smaller",
        plan[rel],
        {
            "count": 2,
            "code": "misc",
            "idiom": 'Expression has type "…"',
            "idiom_count": 1,
        },
    )
    chk(
        "one file's findings come back in line order with their code and message (W743)",
        findings_of(records, rel),
        [
            (3, 0, "misc", 'Expression has type "Any"'),
            (9, 0, "no-untyped-def", "Function is missing a type annotation"),
        ],
    )

    def call(line, name):
        text = f'Call to untyped function "{name}" in typed context'
        return (rel, line, 0, "no-untyped-call", text)

    named = {call(5, "gate"), call(6, "gate"), call(7, "main")}
    named.add((rel, 8, 0, "misc", 'Expression has type "Any"'))
    chk(
        "the hub finder counts untyped callee names and ignores other findings (W743)",
        callees_of(named),
        Counter({"gate": 2, "main": 1}),
    )
    chk(
        "a file with no findings gives an empty list, never an error",
        findings_of(records, "no/such/file.py"),
        [],
    )
    print("typing_census selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
