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

    # ── UNRESOLVED, triaged by READING each symbol's context in the log ──
    # ⚑ EACH LINE BELOW IS A VERDICT WITH A CITATION, NOT A DISMISSAL.  A waiver
    # that says "not a real item" without saying how that was established is an
    # exemption list growing into a blindfold.
    "⊕LOCK-ANIM": "superseded — the log states ⊕WALLPAPER-LIVE supersedes it (:3401)",
    "⊕LOCK-AUTH": "a sub-risk CONSTRAINT (never replace the auth widget), honored as "
                  "a decision, not a work item (:2976, :2986)",
    "⊕AZR-LIT": "deliberately unnumbered — 'derivable by composing the two existing "
                "rules; left open, unnumbered' (:123)",
    "⊕SHAPE-AA-TUNE": "conditional on a LIVE observation — 'if Qt Shape AA still soft "
                      "on this GPU' (:4257); it has no standing until someone looks",
    "⊕TERM-ALACRITTY": "named once as a BONUS off ⊕KONSOLE's same 16 colours (:2843); "
                       "an aspiration mentioned in passing, never scoped",
    "⊕TERM-FOOT": "as ⊕TERM-ALACRITTY — the same single bonus mention (:2843)",
    "⊕SOLVER-CEILING-GHOST-SPLASH": "named only inside another item's parenthetical "
                                    "describing the in-flight splash work (:3922, :3964)",
    "⊕SOLVER-SEL-BACKLIT": "the light-ground selection-contrast residue; its substance "
                           "was discharged by the @SELECTION fix (12/12 pairs now clear, "
                           "worst 5.52:1) — the symbol outlived the problem",
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
        # ⚑ THESE ONCE PINNED TWO SPECIFIC FINDINGS, AND THE PIN WENT STALE THE
        # RIGHT WAY.  The selftest asserted it detected the ⊕RENDER-GATE and
        # ⊕SEG-FONT-PROJECT contradictions, with a note that failure meant either
        # the log was fixed or the detector had gone blind. The log turned out to
        # be right and the READER wrong — both findings dissolved — so the
        # assertions failed exactly as intended, and the pre-commit gate caught
        # it. Pinning a finding tests the SUBJECT; what wants testing is the
        # DETECTOR, which must still discriminate after its subject changes.
        check("the three finding classes are all reachable",
              sorted(f), ["CONTRADICTION", "UNGATED", "UNRESOLVED"])
        check("finds ungated closures", len(f["UNGATED"]) > 0, True)
        # A contradiction must be RECOGNISED when one exists: closed-and-open is
        # the predicate, so a symbol in both sets must land in CONTRADICTION.
        import json as _json
        import subprocess as _sp
        d = _json.loads(_sp.run([sys.executable, INDEX, "--json"],
                                capture_output=True, text=True, cwd=ROOT).stdout)
        open_all = {s for v in d["open"].values() for s in v}
        closed = {s for s, x in d["symbols"].items() if x["closed"]}
        check("no symbol is closed AND open (else CONTRADICTION must list it)",
              sorted(closed & open_all), sorted(f["CONTRADICTION"]))
        # ⚑ NO STALE WAIVERS.  A waiver naming a symbol that is no longer a
        # finding is an exemption nobody has re-examined — the way a waiver list
        # decays into a blindfold. (Written and then caught: the first version of
        # this check ended in `or True`, which cannot fail — the vacuous-claim
        # shape the whole worklist exists to refuse.)
        all_found = {s for d_ in f.values() for s in d_}
        check(f"no waiver is stale ({sorted(set(WAIVERS) - all_found)})",
              sorted(set(WAIVERS) - all_found), [])
    print("check_cotype_coherence selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
