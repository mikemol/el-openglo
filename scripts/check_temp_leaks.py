#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_temp_leaks.py — what a generator leaves in the temp dir when it exits (W784).

⚑ WHY. /var/tmp held 12018 leaked `el-openglo-lnf-*` directories (github-42, 2026-10-29), which with
the other leaks filled the zram mount behind /tmp and /var/tmp until it went emergency read-only and
the host needed a reboot. The biggest was `make_deb.LNF_STAGE`, a `mkdtemp` that ran at IMPORT, so
every process that imported make_deb left one. Nothing measured it, so nothing could notice it grow.
This runs each SUBJECT in its own subprocess with a PRIVATE TMPDIR and lists what is left there when
the subprocess has exited: the count is exact, and the host's /var/tmp is not touched.

    scripts/check_temp_leaks.py --json   # what each subject left, for policy/temp_leaks.rego
    scripts/check_temp_leaks.py --selftest

⚑ WEAKNESS, STATED. It measures the SUBJECTS it lists, not every generator: a temp dir made by a
code path no subject reaches is not seen, and check_urgency_cues is measured for ONE variant only
(its stills are kept when --stills DIR asks, otherwise removed before it returns). A subject that
cannot run here (a missing optional dependency, or no qml runner) is `withheld`, never clean.
"""

import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# subject name -> the python source its subprocess runs, from ROOT with scripts/ on the path
SUBJECTS = {
    "import make_deb": "import make_deb",
    "check_cursors.measure": "import check_cursors; check_cursors.measure()",
    # one variant keeps it light. measure returns early with no cases when the qml runner is absent, which
    # would read as a clean directory over nothing: exit 3 then, so it is `withheld`, never clean
    "check_urgency_cues.measure": (
        "import sys; import check_urgency_cues as C; "
        "sys.exit(0 if C.measure(only='EL-Openglo')['cases'] else 3)"
    ),
    # three trees staged with a no-op stager: the cache keeps ON PURPOSE its newest KEEP of them, and
    # the policy bounds it (W787); an unbounded cache is the leak W784 removed from /var/tmp
    "staging_cache.shared_stage": (
        "import staging_cache as S; "
        "[S.shared_stage(stager=lambda d: None, key=c * 64) for c in 'abc']"
    ),
}
# a subject measured elsewhere on purpose, with the reason it is not run here
DEFERRED: dict[str, str] = {}
# directories a subject keeps on purpose (the shared staged-tree cache, W787): not a leak, but BOUNDED
# by policy/temp_leaks.rego (at most `cache_keep` trees, no .part-* leftover)
PERSISTENT = frozenset({"el-openglo-stage"})


def run_subject(name, source):
    """{subject, rc, leaked}: the entries left in a private TMPDIR after `source` ran and exited."""
    with tempfile.TemporaryDirectory(prefix="temp-leaks-") as private:
        env = dict(os.environ, TMPDIR=private)
        env["PYTHONPATH"] = os.pathsep.join([ROOT, os.path.join(ROOT, "scripts")])
        r = subprocess.run(
            [sys.executable, "-c", source],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        names = sorted(os.listdir(private))
        return {
            "subject": name,
            "rc": r.returncode,
            "leaked": [n for n in names if n not in PERSISTENT],
            # a directory a subject keeps ON PURPOSE, with what it holds: bounded by the policy
            "persistent": {
                n: sorted(os.listdir(os.path.join(private, n)))
                for n in names
                if n in PERSISTENT
            },
            "stderr": r.stderr[-200:],
        }


def measure():
    """The facts: each subject's leftovers, and what could not be run or is deferred."""
    cases, withheld = [], []
    for name, source in SUBJECTS.items():
        got = run_subject(name, source)
        if got["rc"] != 0:
            withheld.append(f"{name}: exited {got['rc']}: {got['stderr']}")
        else:
            cases.append(
                {
                    "subject": name,
                    "leaked": got["leaked"],
                    "persistent": got["persistent"],
                }
            )
    for name, why in DEFERRED.items():
        withheld.append(f"{name}: deferred — {why}")
    import staging_cache

    return {"cases": cases, "withheld": withheld, "cache_keep": staging_cache.KEEP}


def main(argv):
    args = argv[1:]
    for a in args:
        if a not in ("--json", "--selftest"):
            print(f"check_temp_leaks: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in args:
        return 0 if _selftest() else 1
    if "--json" not in args:
        print("check_temp_leaks: needs --json or --selftest", file=sys.stderr)
        return 2
    print(json.dumps(measure(), indent=2))
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    leaky = (
        "import tempfile; tempfile.mkdtemp(prefix='leak-'); "
        "tempfile.mkdtemp(prefix='leak-')"
    )
    clean = "import tempfile\nwith tempfile.TemporaryDirectory(prefix='clean-'): pass"
    got = run_subject("leaky", leaky)
    chk(
        "a subject that leaves two mkdtemp dirs is SEEN leaving two",
        (got["rc"], [n.split("-")[0] for n in got["leaked"]]),
        (0, ["leak", "leak"]),
    )
    got = run_subject("clean", clean)
    chk("a subject that cleans up leaves nothing", (got["rc"], got["leaked"]), (0, []))
    keeper = (
        "import os, tempfile; "
        "d = os.path.join(tempfile.gettempdir(), 'el-openglo-stage'); "
        "os.makedirs(os.path.join(d, 'stage-x')); tempfile.mkdtemp(prefix='leak-')"
    )
    got = run_subject("keeper", keeper)
    chk(
        "a kept cache dir is PERSISTENT with its entries, any other leftover is still a leak",
        (
            [n.split("-")[0] for n in got["leaked"]],
            got["persistent"],
        ),
        (["leak"], {"el-openglo-stage": ["stage-x"]}),
    )
    got = run_subject("broken", "raise SystemExit(3)")
    chk("a subject that fails is reported by its exit code", got["rc"], 3)
    import check_cursors

    chk(
        "the cursors subject's entry point exists (the name its subprocess calls)",
        callable(check_cursors.measure),
        True,
    )
    m = measure()
    chk(
        "every listed subject is accounted for: a case or a withheld line",
        len(m["cases"]) + len(m["withheld"]),
        len(SUBJECTS) + len(DEFERRED),
    )
    ran = {c["subject"] for c in m["cases"]}
    chk(
        "the light subjects ran (not withheld by a crash) and every subject that ran leaves nothing",
        (
            {"import make_deb", "check_cursors.measure"} <= ran,
            [c["subject"] for c in m["cases"] if c["leaked"]],
        ),
        (True, []),
    )
    print("check_temp_leaks selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv))
