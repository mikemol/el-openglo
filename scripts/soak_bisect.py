#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""soak_bisect.py — which marquee input costs the CPU: one Pod soak per input, one table.

⚑ WHY (el-openglo:W520; operator 2026-10-12: the widget pinned plasmashell near 90 % CPU). The
full pummelling soak reproduced a heavy CPU cost offscreen (59 % of one core); this runs the
SAME soak once per input switched on ALONE (marquee_soak.py MIXES) after a baseline of normal
items only, and prints each run's CPU and memory so the costly input names itself.

    scripts/soak_bisect.py --image REF [--seconds N] [--only a,b]   # sequential Pods
    scripts/soak_bisect.py --selftest

Each run is `marquee_soak.py stage` then `soak_pod.py` (so the Pod rules of soak_pod apply:
1 GiB, TTL, deleted on exit). A run that prints no summary is reported as such, never as a
zero. The table reads: mix, CPU % of one core, CPU seconds, last and peak RSS (MB), trace
lines (the board's progress: fewer means slower paints).

WEAKNESS: single runs, no repeats: a difference smaller than the run-to-run noise (not yet
measured here) is not a finding. The Pod's 1-core limit caps the CPU % at 100. The offscreen
software scene graph only (see marquee_soak.py).
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FLAGS = {"--image", "--seconds", "--only", "--selftest"}


def mixes(only=None):
    """[(label, mix tuple, settings)]: the baseline, an idle board (no events), each input alone,
    all of them together, then the baseline under settings that change the BOARD (the ghost field
    off, a larger pitch so fewer pips, a slower scroll)."""
    sys.path.insert(0, HERE)
    import marquee_soak as MS

    rows = [("baseline", (), ""), ("idle", ("idle",), "")]
    rows += [(m, (m,), "") for m in MS.MIXES]
    rows += [("all", MS.MIXES, "")]
    rows += [
        ("noghost", (), "showField=false"),
        ("bigpitch", (), "pitchScale=1.5"),
        ("slow", (), "speed=1"),
    ]
    return [r for r in rows if only is None or r[0] in only]


def parse_summary(text):
    """The summary dict from a soak_pod log (its first line starting with a samples object)."""
    for line in text.splitlines():
        if line.startswith('{"samples"'):
            return json.loads(line)
    return None


def row(label, s):
    if s is None:
        return f"{label:<10} NO SUMMARY (the Pod printed none)"
    ex = s.get("exercised", {})
    rss = s.get("VmRSS", {})
    return (
        f"{label:<10} cpu {s.get('cpu_pct_mean', '?'):>6} %  {s.get('cpu_s', '?'):>7} s  "
        f"rss last {rss.get('last', 0) // 1024:>4} peak {rss.get('peak', 0) // 1024:>4} MB  "
        f"trace {ex.get('trace', '?'):>5}"
    )


def run_one(label, mix, settings, image, seconds):
    with tempfile.TemporaryDirectory() as td:
        d = os.path.join(td, "s")
        stage = [os.path.join(HERE, "marquee_soak.py"), "stage", d]
        stage += ["--seconds", str(seconds), "--mix", ",".join(mix) or "none"]
        if settings:
            stage += ["--set", settings]
        subprocess.run([sys.executable, *stage], check=True, capture_output=True)
        pod = [os.path.join(HERE, "soak_pod.py"), d, "--image", image]
        pod += ["--seconds", str(seconds), "--name", f"soak-bisect-{label}"]
        r = subprocess.run(
            [sys.executable, *pod], capture_output=True, text=True, check=False
        )
    return parse_summary(r.stdout)


def _selftest():
    ok = True

    def chk(label: str, got: object, want: object) -> None:
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    labels = [m[0] for m in mixes()]
    chk(
        "the bisect covers a baseline, an idle board, every input alone, all together, "
        "and three board settings",
        (labels[:2], labels[-3:], len(labels)),
        (["baseline", "idle"], ["noghost", "bigpitch", "slow"], 13),
    )
    chk(
        "a settings row carries its override and no events change",
        [m for m in mixes({"noghost"})],
        [("noghost", (), "showField=false")],
    )
    chk("only= narrows the rows", [m[0] for m in mixes({"flash"})], ["flash"])
    log = 'noise\n{"samples": 3, "cpu_pct_mean": 12.5, "cpu_s": 4.0}\n---SAMPLES---\n'
    chk("the summary is found in a log", parse_summary(log)["cpu_pct_mean"], 12.5)
    chk("a log with no summary is None, never zero", parse_summary("nothing"), None)
    chk("a missing summary prints as such", "NO SUMMARY" in row("x", None), True)
    print("soak_bisect selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    args = argv[1:]
    for a in args:
        if a.startswith("--") and a not in FLAGS:
            print(f"soak_bisect: unknown flag '{a}'", file=sys.stderr)
            return 2
    if "--selftest" in args:
        return 0 if _selftest() else 1
    opts = {"--seconds": "100"}
    for flag in ("--image", "--seconds", "--only"):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                print(f"soak_bisect: {flag} needs a value", file=sys.stderr)
                return 2
            opts[flag] = args.pop(i + 1)
            args.pop(i)
    if "--image" not in opts or args:
        print(
            "usage: soak_bisect.py --image REF [--seconds N] [--only a,b]",
            file=sys.stderr,
        )
        return 2
    only = set(opts["--only"].split(",")) if "--only" in opts else None
    todo = mixes(only)
    if not todo:
        print("soak_bisect: --only matched no row", file=sys.stderr)
        return 2
    seconds = int(opts["--seconds"])
    done = 0
    for label, mix, settings in todo:
        s = run_one(label, mix, settings, opts["--image"], seconds)
        done += s is not None
        print(row(label, s), flush=True)
    print(f"soak_bisect: {done} of {len(todo)} run(s) produced a summary")
    return 0 if done == len(todo) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
