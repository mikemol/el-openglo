#!/usr/bin/env python3
"""readme_fragments.py — the README's POPULATIONS, written from the tools that declare them (W69).

⚑ WHY THIS EXISTS.  README.md is a paperkit projection (paper.toml at the repo
root, claims in catalog/readme/readme.bib). A claim is one sentence with one
check; a POPULATION — sixteen emitters, six variants, fifty-six pictures,
forty-nine closed capabilities — is not a sentence, and typing it into the bib
by hand is exactly the hand-enumeration that drifted the old README to 10 of 16
emitters and 2 of 56 pictures. paperkit places a data file as an `emit:` asset
(a table it builds itself, or a raw block), so each population is WRITTEN here
from its declaring authority and placed by the projection:

    roster.tsv        emitters.ROLES + emitters.ORDER          (every declared module, its role)
    palette.tsv       make_preview.parse_scheme per variant     (the roles each scheme solves to;
                      columns = variant_roster.ordered(), GRID's declared order)
    capabilities.tsv  check_symbol.CLOSED                       (every closed symbol with a witness)
    gallery.md        render_screens.plan_all()                 (every declared picture, root-relative)

    scripts/readme_fragments.py --write     # (re)write catalog/readme/<fragment>
    scripts/readme_fragments.py --list      # each fragment, its authority, and whether it is current
    scripts/readme_fragments.py --selftest

Currency is JUDGED by policy/readme.rego over scripts/check_readme.py --json,
which calls `generate()` here and compares — so a fragment that lags its
authority is a DENY, never a silently stale table on the front page.

WEAKNESS, STATED.  palette.tsv reads the COMMITTED .colors files, so it is
current with the schemes as emitted, not with a re-solve nobody ran. The
gallery links pictures by their declared name; whether each picture exists and
is current is @SCREENS' and @CURRENCY's question, not this one's.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "catalog", "readme")
for p in (ROOT, os.path.join(ROOT, "scripts"), os.path.join(ROOT, "catalog", "library")):
    if p not in sys.path:
        sys.path.insert(0, p)


def roster_tsv():
    import emitters as E
    why = dict(E.ORDER)
    rows = ["module\trole\tstep"]
    for role in ("authority", "emitter", "colourless", "packager"):
        for m in E.declared(role):
            # ⚑ `@` IS WRITTEN AS AN ENTITY. paperkit's table renderer escapes
            # `[` `]` so a cell cannot forge a [@key] citation, but its gate also
            # reads a BARE `@word` as one: ORDER's "GTK3 @define-color" failed the
            # gate as "undefined citations: define-color" (measured, W69). The
            # entity renders as `@` and is not a citation.
            rows.append(f"{m}\t{role}\t{why.get(m, '').replace('@', '&#64;')}")
    return "\n".join(rows) + "\n"


def palette_tsv():
    """Columns are the ROSTER in GRID's declared order (variant_roster.ordered()), never
    render_screens.VARIANTS — check_readme compares that list to the roster (R4)."""
    import make_preview as MP
    import variant_roster as VR
    vs = VR.ordered()
    schemes = {v: MP.parse_scheme(v) for v in vs}
    roles = [k for k, val in schemes[vs[0]].items() if isinstance(val, str)]
    rows = ["role\t" + "\t".join(vs)]
    for r in roles:
        rows.append(r + "\t" + "\t".join(f"`{schemes[v][r]}`" for v in vs))
    return "\n".join(rows) + "\n"


def capabilities_tsv():
    import check_symbol as CS
    rows = ["symbol\tcapability (as its witness states it)"]
    for s in sorted(CS.CLOSED):
        rows.append(f"{s}\t{CS.CLOSED[s][0]}")
    return "\n".join(rows) + "\n"


def gallery_md():
    import render_screens as RS
    import variant_roster as VR
    d = os.path.relpath(RS.SCREENS, ROOT)
    outs = RS.plan_all()
    lines = [f"![all six variants, every still surface]({d}/strip.png)", ""]
    for v in VR.ordered():              # one section per DECLARED variant, in GRID's order
        mine = [fn for fn, var, _how in outs if var == v]
        sheet = [fn for fn in mine if fn.startswith("sheet-")]
        anims = [fn for fn, var, how in outs if var == v and how[0] in ("marquee", "aperture-text") and fn in
                 {a for a, _v, _h in RS.plan_animations()}]
        stills = [fn for fn, var, _h in RS.plan() if var == v]
        lines += [f"### {v}", ""]
        lines += [f"![{v}]({d}/{fn})" for fn in sheet] + [""]
        lines += [f"![{v}: {fn[:-4]}]({d}/{fn})" for fn in anims] + [""]
        lines.append("Stills: " + ", ".join(f"[{fn[:-4]}]({d}/{fn})" for fn in stills) + ".")
        lines.append("")
    rest = [fn for fn, var, _h in outs if var is None and fn != "strip.png"]
    lines.append("Index: " + ", ".join(f"[{fn}]({d}/{fn})" for fn in rest) + ".")
    return "\n".join(lines) + "\n"


FRAGMENTS = {
    "roster.tsv": ("emitters.ROLES", roster_tsv),
    "palette.tsv": ("make_preview.parse_scheme", palette_tsv),
    "capabilities.tsv": ("check_symbol.CLOSED", capabilities_tsv),
    "gallery.md": ("render_screens.plan_all", gallery_md),
}


def generate():
    """{fragment: text} — what each fragment must hold, from its authority now."""
    return {name: fn() for name, (_auth, fn) in FRAGMENTS.items()}


def committed(name):
    p = os.path.join(OUT, name)
    return open(p, encoding="utf-8").read() if os.path.isfile(p) else None


def main(argv):
    known = {"--write", "--list", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"readme_fragments: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    gen = generate()
    if "--write" in argv:
        os.makedirs(OUT, exist_ok=True)
        for name, text in gen.items():
            with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
                fh.write(text)
        print(f"readme_fragments: wrote {len(gen)} of {len(FRAGMENTS)} fragment(s) -> "
              f"{os.path.relpath(OUT, ROOT)}")
        return 0
    if "--list" in argv:
        stale = 0
        for name, (auth, _fn) in FRAGMENTS.items():
            ok = committed(name) == gen[name]
            stale += not ok
            print(f"{name:18s} {auth:28s} {'current' if ok else 'STALE'}")
        print(f"\nreadme_fragments: {len(FRAGMENTS) - stale} of {len(FRAGMENTS)} current")
        return 0
    print("usage: readme_fragments.py --write | --list | --selftest", file=sys.stderr)
    return 2


def _selftest():
    """The generators SEE their populations: none is empty, and each names what it
    claims to — so a fragment's all-current differs from a fragment of nothing."""
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    import emitters as E
    import render_screens as RS
    import check_symbol as CS
    gen = generate()
    chk("every roster module is a row", all(f"\n{m}\t" in gen["roster.tsv"] for m in E.ROLES), True)
    import variant_roster as VR
    chk("the palette columns are the roster, in GRID's order",
        gen["palette.tsv"].splitlines()[0].split("\t")[1:], VR.ordered())
    chk("every declared variant is a gallery section",
        all(f"### {v}\n" in gen["gallery.md"] for v in VR.ordered()), True)
    chk("every closed symbol is a capability row", all(f"\n{s}\t" in gen["capabilities.tsv"] for s in CS.CLOSED), True)
    chk("every declared picture is linked", all(f"/{fn})" in gen["gallery.md"] for fn, _v, _h in RS.plan_all()), True)
    print("readme_fragments selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv))
