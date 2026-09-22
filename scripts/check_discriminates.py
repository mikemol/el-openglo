#!/usr/bin/env python3
"""check_discriminates.py — does a named check FLIP when a named input is corrupted?

⚑ THE QUESTION THIS SETTLES, AND WHY IT COULD NOT BE ANSWERED BY READING. Run in
full for the first time on 2026-09-22, paperkit's Δ grader reported 66 of 72
checks `indeterminate` with one identical message: "corrupting EVERY project
input AT ONCE leaves it green — it is blind to all project content". Two
hypotheses fit that evidence and they demand opposite work:

  H1  the checks really are blind, and the 73-claim green is uninformative
  H2  the GRADER's corruption does not reach what the checks read — if a check's
      footprint is derived statically, every check opening files through
      os.path.join(ROOT, …) has an EMPTY footprint, so "corrupt every input"
      corrupts nothing it touches. That is build_graph's 205 computed relations,
      one level up.

⚑ SIXTY-SIX DIFFERENT CHECKS FAILING IDENTICALLY IS THE SIGNATURE OF ONE COMMON
CAUSE, not of 66 independent blindnesses — and reading a blind instrument's
uniform answer as a fact about the subject is the error this repo keeps finding.
So: perturb ONE input, run ONE check, and see.

    scripts/check_discriminates.py --list                  # the declared probes
    scripts/check_discriminates.py --probe <name>          # run one
    scripts/check_discriminates.py --json                  # run all, as data
    scripts/check_discriminates.py --selftest              # the harness can SEE a flip

⚑ IT RESTORES THE FILE ON EVERY PATH, including a crash and a KeyboardInterrupt,
because a corruption that outlives the probe is a corrupted repository. The
original bytes are held in memory and written back in a finally.

WEAKNESS, STATED: a flip proves the check reads THAT file and reacts to THAT
perturbation. It does NOT prove the check is adequate — a check that notices a
mangled key while ignoring a wrong colour still flips here. This answers
"blind or not", which is the question actually in dispute, and nothing finer.
⚑ AND A NON-FLIP IS NOT A VERDICT ON THE CHECK EITHER: it may mean the
perturbation was not one the check's question ranges over. The probe names what
it corrupted so a reader can judge that rather than trust the boolean.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (name, check argv, input path, what to corrupt, how). `how` is (old, new) — a
# literal substring swap, so the perturbation is legible in the report rather
# than being "some mutation".
PROBES = (
    # ⚑ THE EMITTED .colors IS THE WRONG TARGET, AND MEASURING THAT WAS THE POINT.
    # Both palette probes aimed at EL-Amber.colors and neither flipped — not
    # because the checks are blind, but because the tree reads ONE palette through
    # two AUTHORITIES (make_preview.parse_scheme, make_schemes.GRID) and .colors is
    # a generated artifact downstream of them. A probe aimed at an output cannot
    # grade a check that reads the source.
    # ⚑ AND THE NON-FLIP IS ITSELF A FINDING, KEPT: nothing here notices a
    # corrupted EMITTED .colors. check_selection_contrast answers "is the SOLVE
    # good", never "is the artifact on disk what the solve says" — which is
    # @CURRENCY's question, and why these two are separate obligations.
    # ⚑ AIM AT WHAT THE CHECK ACTUALLY READS, AND THAT IS THE HARD PART. Three
    # probes in a row missed: DecorationFocus (the check reads ForegroundNormal /
    # ForegroundActive), then make_preview.py (not among its importers), then
    # make_schemes.py. With the whole repo in front of me I could not GUESS a
    # check's inputs — which is exactly why the Δ grader's corruption misses and
    # reports "blind to all project content". The inputs are undeclared; the
    # grader and I are both inferring, and inference is what W61 replaces.
    ("selection-contrast/emitted-colors",
     ["scripts/check_selection_contrast.py"], "EL-Amber.colors",
     ("[Colors:Selection]", "[Colors:SelectionWAS]")),
    # ⚑ AND THE SECOND AUTHORITY IS A DIFFERENT FILE PER CHECK, WHICH IS THE
    # MECHANISM. A probe at make_preview.py did not flip check_selection_contrast
    # — measured by `pycodemod --importers make_preview`, that check is NOT among
    # its 16 importers. I had been GUESSING which file a check reads, and so is
    # the Δ grader: with inputs undeclared, a corruption aimed by inference misses,
    # and the miss reports as "the check is blind to all project content".
    ("selection-contrast/authority",
     ["scripts/check_selection_contrast.py"], "make_schemes.py",
     ("GRID = _solved_grid()", "GRIDWAS = _solved_grid()")),
    # ⚑ AIMED AT THE POPULATION, NOT THE PREDICATE. check_token_source asks a
    # STRUCTURAL question ("does this emitter import an authority?") that a
    # def-rename inside the authority cannot disturb — so the make_schemes probe
    # was testing nothing here and read as a non-flip. The defect is its
    # POPULATION: remove a declared emitter and "16 of 16" becomes "15 of 15".
    # The perturbation must therefore remove a MEMBER, which for this check means
    # breaking the roster's agreement with the tree.
    ("token-source/roster",
     ["scripts/check_token_source.py"], "emitters.py",
     ('"make_css":             "emitter"', '"make_cssWAS":          "emitter"')),
    ("css/emitted-sheet",
     ["scripts/check_css.py"], "make_css.py",
     ("def _is_rgb", "def _is_rgbWAS")),
)


def _drop_bytecode(path):
    """Remove any cached .pyc for `path`, both writing and restoring.

    ⚑ A RESTORED FILE IS NOT A RESTORED MODULE (measured 2026-09-22). Python
    validates a .pyc on (mtime, size). This tool's perturbations are substring
    swaps that are often the SAME LENGTH — the roster probe pads the replacement
    to keep the dict aligned — and a write plus a restore inside one second give
    the same mtime. So the corrupted bytecode outlived the corrupted source, and
    the very next run of an unrelated tool read `make_cssWAS` out of a file that
    said `make_css`. ⚑ THAT IS A CONTAMINATION PATH BETWEEN PROBES: a later probe
    would have graded a check against a tree nobody could see was wrong."""
    if not path.endswith(".py"):
        return
    d, base = os.path.split(path)
    cache = os.path.join(d, "__pycache__")
    if not os.path.isdir(cache):
        return
    stem = base[:-len(".py")]
    for f in os.listdir(cache):
        if f.startswith(stem + ".") and f.endswith(".pyc"):
            try:
                os.remove(os.path.join(cache, f))
            except OSError:
                pass


def _run(argv):
    r = subprocess.run([sys.executable] + [os.path.join(ROOT, argv[0])] + argv[1:],
                       capture_output=True, text=True, cwd=ROOT)
    return r.returncode, (r.stdout + r.stderr).strip().splitlines()[-1:] or [""]


def probe(p):
    """{name, before, after, flipped, …} for one probe. The file is restored on
    every path — a corruption that outlives the probe is a corrupted repo."""
    name, argv, rel, (old, new) = p
    path = os.path.join(ROOT, rel)
    if not os.path.isfile(path):
        return {"name": name, "withheld": f"{rel} is not in the tree"}
    original = open(path, "rb").read()
    hits = original.count(old.encode())
    if hits == 0:
        # ⚑ A PERTURBATION THAT CHANGES NOTHING GRADES NOTHING. If the anchor is
        # absent the file was never corrupted, and a green check afterwards would
        # be read as "the check is blind" when it means "the probe did nothing".
        return {"name": name, "withheld": f"{rel} does not contain {old!r} — nothing was perturbed"}
    if hits > 1:
        # ⚑ AN AMBIGUOUS ANCHOR IS NOT A DETERMINATE PERTURBATION, and this cost a
        # wrong reading before it was caught (2026-09-22): the anchor '"make_css"'
        # occurs in emitters.ORDER before emitters.ROLES, so replace(…, 1) hit the
        # WRONG declaration and the probe reported "does NOT flip" about a
        # corruption it had never applied where it meant to. A silently-first
        # match is the same defect as a silently-shrinking population: the report
        # describes something other than what the reader believes was measured.
        return {"name": name,
                "withheld": f"{rel} contains {old!r} {hits} times — an ambiguous anchor "
                            f"perturbs whichever comes first; make it unique"}
    rc_before, out_before = _run(argv)
    try:
        open(path, "wb").write(original.replace(old.encode(), new.encode(), 1))
        _drop_bytecode(path)
        rc_after, out_after = _run(argv)
    finally:
        open(path, "wb").write(original)
        _drop_bytecode(path)
    return {"name": name, "check": argv[0], "input": rel,
            "perturbation": f"{old!r} -> {new!r}",
            "rc_before": rc_before, "rc_after": rc_after,
            "before": out_before[0], "after": out_after[0],
            "flipped": rc_before == 0 and rc_after != 0}


def measure():
    cases = [probe(p) for p in PROBES]
    return {"cases": cases,
            "n": len(cases),
            "flipped": sum(1 for c in cases if c.get("flipped")),
            "withheld": sum(1 for c in cases if "withheld" in c)}


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}"
              + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    print("check_discriminates selftest:")
    chk("the probe population is not empty", len(PROBES) > 0, True)
    # ⚑ THE HARNESS MUST SEE A FLIP IT KNOWS IS THERE. A probe whose anchor is
    # absent must report WITHHELD, never a quiet non-flip — the two readings
    # demand opposite work, which is the whole subject of this tool.
    absent = ("absent-anchor", ["scripts/check_selection_contrast.py"], "EL-Amber.colors",
              ("THIS-STRING-IS-NOT-IN-THE-FILE", "x"))
    chk("an anchor that is absent is WITHHELD, not a non-flip",
        "withheld" in probe(absent), True)
    missing = ("absent-file", ["scripts/check_selection_contrast.py"], "no-such-file.colors",
               ("a", "b"))
    chk("a missing input is WITHHELD", "withheld" in probe(missing), True)
    # ⚑ AN AMBIGUOUS ANCHOR MUST BE WITHHELD, NOT SILENTLY FIRST-MATCHED. Measured
    # 2026-09-22: '"make_css"' occurs in emitters.ORDER before emitters.ROLES, so
    # the probe corrupted a declaration it did not mean to and reported "does NOT
    # flip" about a perturbation it had never applied where it intended.
    ambiguous = ("ambiguous-anchor", ["scripts/check_token_source.py"], "emitters.py",
                 ("make_css", "make_cssWAS"))
    chk("an ambiguous anchor is WITHHELD", "withheld" in probe(ambiguous), True)
    # and the file survives every path
    before = open(os.path.join(ROOT, "EL-Amber.colors"), "rb").read()
    probe(PROBES[0])
    chk("the input is restored after a probe",
        open(os.path.join(ROOT, "EL-Amber.colors"), "rb").read(), before)
    # ⚑ AND THE MODULE IS RESTORED, NOT ONLY THE FILE. A same-length swap inside
    # one second leaves a .pyc that (mtime, size) validation accepts, so the
    # corrupted bytecode outlives the corrupted source — a contamination path
    # between probes that no per-probe assertion about the FILE can see.
    roster = os.path.join(ROOT, "emitters.py")
    probe(PROBES[2])
    import subprocess as _sp
    after = _sp.run([sys.executable, os.path.join(ROOT, "emitters.py"), "--drift"],
                    capture_output=True, text=True, cwd=ROOT)
    chk("the module is restored too, not just the file", after.returncode, 0)
    print("check_discriminates selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    known = {"--list", "--json", "--selftest", "--probe"}
    args = list(argv[1:])
    only = None
    if "--probe" in args:
        i = args.index("--probe")
        if i + 1 >= len(args):
            print("check_discriminates: --probe needs a name", file=sys.stderr)
            return 2
        only = args[i + 1]
        del args[i:i + 2]
    for a in args:
        if a not in known:
            print(f"check_discriminates: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in args:
        return _selftest()
    if "--list" in args:
        for name, argv_, rel, (old, new) in PROBES:
            print(f"  {name:28s} {argv_[0]}  <- {rel}  ({old!r} -> {new!r})")
        print(f"\ncheck_discriminates: {len(PROBES)} declared probe(s)")
        return 0
    ps = [p for p in PROBES if only is None or p[0] == only]
    if only is not None and not ps:
        print(f"check_discriminates: no probe named {only!r}; --list shows them",
              file=sys.stderr)
        return 2
    cases = [probe(p) for p in ps]
    if "--json" in args:
        print(json.dumps({"cases": cases, "n": len(cases)}, indent=1))
        return 0
    for c in cases:
        if "withheld" in c:
            print(f"  WITHHELD  {c['name']}: {c['withheld']}")
            continue
        verb = "FLIPS" if c["flipped"] else "does NOT flip"
        print(f"  {verb:14s} {c['name']}")
        print(f"                 corrupt {c['input']}: {c['perturbation']}")
        print(f"                 before rc={c['rc_before']}  {c['before']}")
        print(f"                 after  rc={c['rc_after']}  {c['after']}")
    graded = [c for c in cases if "withheld" not in c]
    if not graded:
        print("\ncheck_discriminates: REFUSED — every probe was withheld; "
              "nothing was graded, which is not the same as nothing being wrong",
              file=sys.stderr)
        return 3
    flipped = sum(1 for c in graded if c["flipped"])
    print(f"\ncheck_discriminates: {flipped} of {len(graded)} graded probe(s) flip "
          f"({len(cases) - len(graded)} withheld)")
    return 0 if flipped == len(graded) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
