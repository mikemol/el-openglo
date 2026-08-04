#!/usr/bin/env python3
"""check_cotype_coherence.py — the design log does not contradict itself.

COTYPE.md is append-only and 4,600 lines long, so its own bookkeeping drifts: a
symbol gets ticked closed in one line and named as pending work in the next, a
closure is asserted without the four-gate verdict the log's own discipline
requires, or a symbol is introduced and then never resolved either way. None of
that is visible by reading — the contradicting lines are usually adjacent, but
the log is far too long to hold at once.

    scripts/check_cotype_coherence.py             # exit 0 iff the log is coherent
    scripts/check_cotype_coherence.py --report    # every finding, by class
    scripts/check_cotype_coherence.py --waivers   # the accepted findings + why

Three coherence rules, each a real defect class measured in this log:

  CONTRADICTION  a symbol marked closed AND listed open in the FINAL ledger.
                 Measured: ⊕RENDER-GATE (ticked ✓, then "wire it into make_deb"
                 as pending BUILD) and ⊕SEG-FONT-PROJECT (ticked "principle
                 proven ✓PoC", also listed under RESEARCH). Both are overclaims:
                 built-but-unwired and proof-of-concept read as done.

  UNGATED        a closure section with no four-gate verdict. The log's own
                 discipline is constructible/reachable/observable/coverable; a
                 closure without it asserts completion rather than showing it.

  UNRESOLVED     a symbol introduced and never closed, never ticked, and never
                 carried into the open set. It has silently fallen out of the
                 worklist — the failure mode this whole repo exists to prevent.

⚑ WAIVERS ARE NAMED AND REASONED, NEVER A BARE COUNT.  A waiver records a finding
this project has decided to accept, with the reason, so the check goes green on a
KNOWN state rather than a lowered bar. An unwaived finding of any class is red.
A waiver naming a symbol that no longer has that finding is itself an error —
stale waivers are how an exemption list becomes a blindfold.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "scripts", "cotype_index.py")

# Findings accepted with a reason.  symbol -> why.  Keep these SHORT and true.
WAIVERS = {
    # UNGATED — closed before the log adopted the four-gate discipline per symbol.
    "⊕AUR": "closed in an early session, before per-symbol four-gate sections",
    "⊕BRT": "early session; gates recorded in prose rather than a gate line",
    "⊕ITO": "early session; gates recorded in prose rather than a gate line",
    "⊕KNB": "early session; gates recorded in prose rather than a gate line",
    "⊕KVT": "early session; gates recorded in prose rather than a gate line",
    "⊕LIT": "early session; gates recorded in prose rather than a gate line",
    "⊕PLA": "early session; gates recorded in prose rather than a gate line",
    "⊕SOLVER-BACKLIT-CVD": "gate verdict folded into the parent solver closure",
    # UNRESOLVED — prose fragments of a longer symbol, not symbols of their own.
    "⊕SOLVER": "prose stem of ⊕SOLVER-* (UI-TOKENS, PERF, SEMANTIC, …)",
    "⊕SOLVER-UI": "prose stem of ⊕SOLVER-UI-TOKENS",
    "⊕PANEL": "prose stem of ⊕PANEL-LAYOUT",
    "⊕ICONS": "prose stem of ⊕ICONS-INHERIT",
    "⊕CURSOR": "prose stem of ⊕CURSOR-INHERIT",
    "⊕HDR": "prose stem of ⊕HDR-EMIT",
    "⊕KVANTUM": "prose spelling of ⊕KVT, which is closed",
    "⊕PARAMETRIC": "prose stem of ⊕PARAMETRIC-PALETTE",
    "⊕SEG-FONT-KERN": "the log marks it closed-by-design (a deliberate non-goal)",
}


def findings():
    """{class: {symbol: detail}} — the coherence findings, from the index."""
    r = subprocess.run([sys.executable, INDEX, "--json"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        return None
    d = json.loads(r.stdout)
    syms, opn = d["symbols"], d["open"]
    open_all = {s for v in opn.values() for s in v}

    out = {"CONTRADICTION": {}, "UNGATED": {}, "UNRESOLVED": {}}
    for s, info in syms.items():
        if info["closed"] and s in open_all:
            buckets = ",".join(info["buckets"])
            out["CONTRADICTION"][s] = f"marked closed ({info['by']}) yet listed open in {buckets}"
        elif info["closed"] and info["by"] == "closure" and info["gates"] == 0:
            out["UNGATED"][s] = "closure section carries no four-gate verdict"
        elif not info["closed"] and s not in open_all:
            out["UNRESOLVED"][s] = "never closed, never ticked, never listed open"
    return out


def main(argv):
    known = {"--report", "--waivers"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_cotype_coherence: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--waivers" in argv:
        for s, why in sorted(WAIVERS.items()):
            print(f"{s}\t{why}")
        return 0

    f = findings()
    if f is None:
        print("check_cotype_coherence: REFUSED — the index would not run; the log "
              "cannot be read structurally", file=sys.stderr)
        return 2
    total = sum(len(v) for v in f.values())

    if "--report" in argv:
        for cls in ("CONTRADICTION", "UNGATED", "UNRESOLVED"):
            for s, why in sorted(f[cls].items()):
                mark = "waived" if s in WAIVERS else "OPEN  "
                print(f"{mark}\t{cls}\t{s}\t{why}")
        return 0

    if total == 0:
        print("check_cotype_coherence: REFUSED — no findings AT ALL, including the "
              "classes known to exist; the index is broken, not the log perfect",
              file=sys.stderr)
        return 2

    unwaived = {cls: {s: w for s, w in d.items() if s not in WAIVERS}
                for cls, d in f.items()}
    n_unwaived = sum(len(v) for v in unwaived.values())

    # A waiver for a finding that no longer exists is itself a defect.
    all_found = {s for d in f.values() for s in d}
    stale = sorted(set(WAIVERS) - all_found)

    if n_unwaived or stale:
        print(f"check_cotype_coherence: REFUSED — {n_unwaived} unwaived finding(s) "
              f"of {total}, {len(stale)} stale waiver(s):", file=sys.stderr)
        for cls in ("CONTRADICTION", "UNGATED", "UNRESOLVED"):
            for s, why in sorted(unwaived[cls].items()):
                print(f"    {cls}  {s}: {why}", file=sys.stderr)
        for s in stale:
            print(f"    STALE WAIVER  {s}: waived, but no longer a finding",
                  file=sys.stderr)
        return 1
    print(f"check_cotype_coherence: {total} of {total} findings waived with a "
          f"reason, 0 unwaived, 0 stale")
    return 0


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    check("every waiver carries a reason", all(WAIVERS.values()), True)
    f = findings()
    check("the index answers", f is not None, True)
    if f is not None:
        # ⚑ THE CHECK MUST FIND THE DEFECTS IT WAS BUILT FROM.  If these two stop
        # appearing, either the log was fixed (then update this) or the detector
        # broke (then it is blind).  Either way it must not pass silently.
        check("detects the ⊕RENDER-GATE contradiction",
              "⊕RENDER-GATE" in f["CONTRADICTION"], True)
        check("detects the ⊕SEG-FONT-PROJECT contradiction",
              "⊕SEG-FONT-PROJECT" in f["CONTRADICTION"], True)
        check("finds ungated closures", len(f["UNGATED"]) > 0, True)
    print("check_cotype_coherence selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
