#!/usr/bin/env python3
"""check_readme.py — MEASURE whether README.md covers what the tree declares (W69).

README.md is a paperkit projection (paper.toml at the root, claims in
catalog/readme/readme.bib); paperkit's own gate refuses drift between README.md
and that projection. What paperkit CANNOT see is whether the claim graph covers
the project — a projection of a thin graph is a faithful thin README, which is
exactly what the hand-written one was (10 of 16 emitters, 2 of 56 pictures, no
variant named). So this measures, per declared population item, whether the
front page names it:

    emitter   every module emitters.ROLES declares           token: the module name
    variant   every variant the ROSTER declares (variant_roster, GRID) token: the variant name
              — render_screens.VARIANTS is compared TO it (`roster_drift`), never used as it
    picture   every output render_screens.plan_all() declares token: its root-relative path
    symbol    every closed symbol check_symbol.CLOSED holds   token: the symbol
    fragment  every readme_fragments population file          fact: committed == generated

    scripts/check_readme.py --json     # the measurement (policy/readme.rego decides)
    scripts/check_readme.py --selftest # the measurement can SEE a missing token and a stale fragment

The requirement is policy/readme.rego, run through `scripts/opa_gate.py readme`.

WEAKNESS, STATED.  "Names it" is a substring test over README.md: it proves the
front page MENTIONS each item, not that the sentence around it is true — that is
each claim's own check. And the populations are read from their authorities, so
an item deleted from BOTH the authority and the README reads clean (it is no
longer declared); that is @EMITTERS / @SCREENS / @REGRESSIONS' question.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")
for p in (ROOT, os.path.join(ROOT, "scripts"), os.path.join(ROOT, "catalog", "library")):
    if p not in sys.path:
        sys.path.insert(0, p)


def populations():
    """[(kind, name, token)] — every item the front page must name, from its authority."""
    import emitters as E
    import render_screens as RS
    import check_symbol as CS
    import variant_roster as VR
    d = os.path.relpath(RS.SCREENS, ROOT)
    out = [("emitter", m, m) for m in sorted(E.ROLES)]
    out += [("variant", v, v) for v in VR.ordered()]
    out += [("picture", fn, f"{d}/{fn}") for fn, _v, _h in RS.plan_all()]
    out += [("symbol", s, s) for s in sorted(CS.CLOSED)]
    return out


def measure(readme_text=None, fragments=None):
    import readme_fragments as RF
    if readme_text is None:
        readme_text = open(README, encoding="utf-8").read() if os.path.isfile(README) else None
    items = [{"kind": k, "name": n, "named": readme_text is not None and tok in readme_text}
             for k, n, tok in populations()]
    gen = RF.generate()
    frags = [{"name": n, "current": (fragments or {}).get(n, RF.committed(n)) == gen[n]}
             for n in sorted(RF.FRAGMENTS)]
    import render_screens as RS
    import variant_roster as VR
    return {"readme": readme_text is not None, "items": items, "fragments": frags,
            "roster_drift": VR.drift_facts({"render_screens": RS.VARIANTS})}


def main(argv):
    known = {"--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_readme: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    print("usage: check_readme.py --json | --selftest  (the verdict: scripts/opa_gate.py readme)",
          file=sys.stderr)
    return 2


def _selftest():
    """The measurement can SEE: an empty README names nothing; a README naming every
    token names everything; a fragment that differs from its generation is not current."""
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    pops = populations()
    chk("every population kind is non-empty",
        sorted({k for k, _n, _t in pops}), ["emitter", "picture", "symbol", "variant"])
    empty = measure(readme_text="")
    chk("an empty README names nothing", any(i["named"] for i in empty["items"]), False)
    full = measure(readme_text="\n".join(t for _k, _n, t in pops))
    chk("a README naming every token names all", all(i["named"] for i in full["items"]), True)
    stale = measure(readme_text="", fragments={"gallery.md": "stale"})
    chk("a differing fragment is not current",
        [f["current"] for f in stale["fragments"] if f["name"] == "gallery.md"], [False])
    import render_screens as RS
    chk("the live render_screens.VARIANTS is the roster", full["roster_drift"], [])
    kept = RS.VARIANTS
    try:
        RS.VARIANTS = [x for x in kept if x != "EL-Amber"]      # a planted drop
        dropped = measure(readme_text="")["roster_drift"]
    finally:
        RS.VARIANTS = kept
    chk("a screen renderer that drops a variant is a fact", [(d["who"], d["variant"]) for d in dropped],
        [("render_screens", "EL-Amber")])
    print("check_readme selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv))
