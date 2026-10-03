#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_runtime_warnings.py — runtime warnings as emit-time tripwires (W53).

catalog/runtime-warnings.json holds one row per class of plasmashell/KWin stderr
line the live host has produced. This MEASURES each row: whether its rule's file
exists, and how many days an unruled row has gone unruled. policy/runtime_warnings.rego
decides (R0 empty, R1 neither rule nor unruled_since, R2 unruled too long, R3 a
rule whose file is gone).

    scripts/check_runtime_warnings.py --json      # the measurement
    scripts/check_runtime_warnings.py --list      # n of m classes ruled
    scripts/check_runtime_warnings.py --selftest
    scripts/opa_gate.py runtime_warnings          # the verdict

WEAKNESS, STATED. The corpus is what the operator pasted: a class never seen is
absent, not refused. A rule is checked for its FILE, not that the cited rule id
in it actually trips this line — that link is the row's claim, read by a human.
Age is calendar days from today, not sessions.
"""
import datetime
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS = os.path.join(ROOT, "catalog", "runtime-warnings.json")


def measure(path=CORPUS, today=None, root=ROOT):
    # the host's LOCAL calendar date, as date.today() gave it (an aware local now, then .date())
    today = today or datetime.datetime.now(datetime.UTC).astimezone().date()
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as e:
        return {"cases": [], "withheld": f"{type(e).__name__}: {e}", "max_unruled_days": None}
    cases = []
    for w in doc.get("warnings", []):
        rule = w.get("rule")
        since = w.get("unruled_since")
        try:
            age = (today - datetime.date.fromisoformat(since)).days if since else None
        except ValueError:
            age = None
        cases.append({"class": w.get("class"), "ruled": bool(rule),
                      "rule_file": rule.get("file") if rule else None,
                      "rule_file_exists": os.path.isfile(os.path.join(root, rule["file"]))
                      if rule and rule.get("file") else None,
                      "unruled_since": since, "unruled_days": age})
    return {"cases": cases, "withheld": None, "max_unruled_days": doc.get("max_unruled_days")}


def _selftest():
    import tempfile
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(("  ok   " if got == want else "  FAIL ") + label
              + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump({"max_unruled_days": 7, "warnings": [
            {"class": "a", "rule": {"file": "no/such.rego", "id": "X"}, "unruled_since": None},
            {"class": "b", "rule": None, "unruled_since": "2026-09-01"}]}, fh)
    m = measure(fh.name, today=datetime.date(2026, 10, 1))
    os.unlink(fh.name)
    chk("a rule whose file is gone is SEEN", m["cases"][0]["rule_file_exists"], False)
    chk("an unruled row's age is measured in days", m["cases"][1]["unruled_days"], 30)
    chk("an unreadable corpus is withheld", measure("/nonexistent.json")["withheld"] is not None, True)
    real = measure()
    chk("the real corpus is non-empty", len(real["cases"]) > 0, True)
    print("check_runtime_warnings selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    known = {"--json", "--list", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_runtime_warnings: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    m = measure()
    if "--json" in argv:
        print(json.dumps(m, indent=1))
        return 0
    if "--list" in argv:
        cs = m["cases"]
        for c in cs:
            state = f"ruled by {c['rule_file']}" if c["ruled"] else f"UNRULED {c['unruled_days']} day(s)"
            print(f"  {c['class']:28} {state}")
        print(f"check_runtime_warnings: {sum(c['ruled'] for c in cs)} of {len(cs)} classes ruled")
        return 0
    print("usage: check_runtime_warnings.py --json | --list | --selftest", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
