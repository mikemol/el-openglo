#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""check_codomain.py — the codomain map: every surface the palette reaches, or could (W42).

Two halves, and only one is typed by hand:

    emitted  READ from check_publishing (the emitters roster x catalog/publishing.md):
             each emitter with the venue(s) its rows name. check_publishing's own
             policy already refuses an emitter with no row, so it is not re-policed.
    gaps     catalog/codomain.json — targets no emitter writes yet, each with a
             contract (the format it must satisfy), venue, licence, reach and cost.

    scripts/check_codomain.py --json      # the measurement (policy/codomain.rego decides)
    scripts/check_codomain.py --list      # n of m surfaces emitted; gaps ranked
    scripts/check_codomain.py --selftest  # the measurement can SEE a bad gap
    scripts/opa_gate.py codomain          # the verdict

rank = reach x (6 - cost): reach and cost are 1-5 judgements recorded in the file,
so the ordering is reproducible, not re-derived per reader.

WEAKNESS, STATED. A gap is only as complete as the file: a surface nobody wrote
down is absent, not refused — the census bounds what was THOUGHT OF. Gap targets
are matched against emitted ones by name (`make_<target>`), so a gap spelled
differently from the emitter that already covers it is not caught.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
GAPS = os.path.join(ROOT, "catalog", "codomain.json")
FIELDS = ("target", "family", "contract", "venue", "licence", "reach", "cost")


def rank(g):
    r, c = g.get("reach"), g.get("cost")
    return r * (6 - c) if isinstance(r, int) and isinstance(c, int) else None


def measure(gaps_path=GAPS):
    import check_publishing as P
    pub = P.measure(P.rows(), P.categories(), P.emitters())
    venues = {}
    for r in pub["rows"]:
        venues.setdefault(r["emitter"].split(" ")[0], []).append(r["venue"])
    emitted = [{"target": c["emitter"].removeprefix("make_"), "emitter": c["emitter"],
                "venues": venues.get(c["emitter"], [])} for c in pub["cases"]]
    try:
        gaps = json.load(open(gaps_path, encoding="utf-8"))["gaps"]
        withheld = None
    except (OSError, ValueError, KeyError) as e:
        gaps, withheld = [], f"{type(e).__name__}: {e}"
    cases = [{**{k: g.get(k) for k in FIELDS},
              "missing": [k for k in FIELDS if g.get(k) in (None, "")],
              "rank": rank(g)} for g in gaps]
    return {"emitted": emitted, "gaps": cases, "gaps_withheld": withheld}


def _selftest():
    import tempfile
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(("  ok   " if got == want else "  FAIL ") + label
              + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump({"gaps": [{"target": "x", "family": "f", "venue": "v", "licence": "Apache-2.0",
                             "reach": 5, "cost": 1}]}, fh)
    m = measure(fh.name)
    os.unlink(fh.name)
    chk("a gap without a contract is SEEN as missing it", m["gaps"][0]["missing"], ["contract"])
    chk("...and ranked reach x (6 - cost)", m["gaps"][0]["rank"], 25)
    chk("an unreadable gaps file is withheld, not empty-and-fine",
        measure("/nonexistent.json")["gaps_withheld"] is not None, True)
    real = measure()
    chk("the real emitted half is non-empty", len(real["emitted"]) > 0, True)
    chk("the real gaps file reads", real["gaps_withheld"], None)
    print("check_codomain selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    known = {"--json", "--list", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_codomain: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    m = measure()
    if "--json" in argv:
        print(json.dumps(m, indent=1))
        return 0
    if "--list" in argv:
        n = len(m["emitted"]) + len(m["gaps"])
        print(f"check_codomain: {len(m['emitted'])} of {n} surfaces emitted; {len(m['gaps'])} gap(s), ranked:")
        for g in sorted(m["gaps"], key=lambda g: -(g["rank"] or 0)):
            print(f"  {str(g['rank']):>3}  {g['target']:24} {g['family']:20} {g['venue']}")
        return 0
    print("usage: check_codomain.py --json | --list | --selftest  (verdict: scripts/opa_gate.py codomain)",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
