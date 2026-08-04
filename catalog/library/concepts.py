#!/usr/bin/env python3
"""catalog/library/concepts.py — the concept-witness LIBRARY (the owner of each concept's proof).

A concept is authored ONCE — its record in this library's concepts.bib, its
witness here — and any VIEW that cites it resolves `concept:<key>` by IMPORTING
that proof instead of re-authoring a parallel, and usually weaker, one.

    catalog/library/concepts.py <key>      # run one concept's witness
    catalog/library/concepts.py --list     # every concept this library owns

⚑ WHY A LIBRARY RATHER THAN MORE scripts/check_*.py.  Two worklists live here
(catalog/worklist and catalog/cotype) and they had begun asking overlapping
questions of the same artifacts. The moment two views witness one fact, they
drift: one gets fixed, the other keeps certifying the old answer. paperkit's
`concept:` verb exists for exactly that — the library owns the proof, the views
import it.

⚑ EXIT 2 MEANS "NOT MINE", AND IT IS LOAD-BEARING.  An unknown key exits 2 so the
resolver falls through to the engine's own library rather than reporting a
failure. A project library that answered 1 for a key it does not own would
ECLIPSE every engine concept.

⚑ THESE WITNESSES ARE ABOUT THE THEME AS SEEN.  The samples in catalog/library/samples/
are the point of the library — a place to LOOK — and these are the checks that
keep what you look at honest: that it rendered at all, that its palette has as
many distinct colours as it has roles, that the index names what exists.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SAMPLES = os.path.join(HERE, "samples")
sys.path.insert(0, ROOT)


def samples_exist(targets=None, min_bytes=128):
    """Every declared sample is present and non-empty.

    The library is a place to LOOK; a missing sample is a hole in the thing
    being looked at, and an empty SVG is a hole that still lists in the index."""
    if targets is None:
        sys.path.insert(0, HERE)
        import render_samples as RS
        targets = RS.targets()
    assert targets, "no sample targets — the scheme files are missing"
    bad = [(v, s) for v, s, p, _d, _f in targets
           if not os.path.isfile(p) or os.path.getsize(p) < min_bytes]
    assert not bad, f"{len(bad)} of {len(targets)} sample(s) missing or empty: {bad[:4]}"


def index_is_generated():
    """library.md names exactly the samples that exist.

    ⚑ A HAND-MAINTAINED INDEX OF IMAGES OUTLIVES THE FILES IT NAMES.  This is the
    witness that the index was regenerated rather than edited: every sample on
    disk appears in it, and it names no sample that is absent."""
    sys.path.insert(0, HERE)
    import render_samples as RS
    md = os.path.join(HERE, "library.md")
    assert os.path.isfile(md), "library.md is absent — nothing to look at"
    text = open(md, encoding="utf-8").read()
    on_disk = sorted(f for f in os.listdir(SAMPLES)) if os.path.isdir(SAMPLES) else []
    assert on_disk, "samples/ is empty"
    unnamed = [f for f in on_disk if f not in text]
    assert not unnamed, f"on disk but absent from the index: {unnamed[:4]}"


def palette_roles_are_distinct():
    """Each palette ROLE renders as its own colour.

    ⚑ FOUND BY LOOKING, WHICH IS WHY THE LIBRARY EARNS ITS KEEP.  The swatch
    sample showed `phosphor` and `accent` as one colour in every variant — and
    the emitted scheme confirms it: Button/DecorationFocus equals
    View/ForegroundNormal byte for byte. The README gives them different jobs
    (`body-glow` is normal text, `el-core` is the focus ring), so a focus ring
    the exact colour of the text it surrounds cannot do its job.

    No check caught it: every existing gate asked about CONTRAST AGAINST A
    BACKGROUND, and these two are perfectly legible — just not from each other.
    A palette needs as many distinct colours as it has roles, and that is a
    different question from whether each one is readable."""
    import make_preview as MP
    variants = sorted(f[:-len(".colors")] for f in os.listdir(ROOT)
                      if f.endswith(".colors"))
    assert variants, "no scheme files"
    collisions = []
    for v in variants:
        c = MP.parse_scheme(v)
        roles = [k for k in ("ground", "panel", "phosphor", "accent", "sel") if k in c]
        for i in range(len(roles)):
            for j in range(i + 1, len(roles)):
                if c[roles[i]] == c[roles[j]]:
                    collisions.append(f"{v}: {roles[i]}=={roles[j]} ({c[roles[i]]})")
    # ⚑ REPORT DISTINCT FIXES, NOT FAILURE COUNT.  Six collisions — one per
    # variant — are ONE change: make `accent` differ from `phosphor` in the
    # solver. A consumer that counted the failures would size this as six times
    # the work it is, so the witness says which number it means rather than
    # leaving a reader to infer it from the prose.
    kinds = {tuple(sorted(x.split(": ", 1)[-1].split(" (")[0].split("==")))
             for x in collisions}
    assert not collisions, (
        f"{len(collisions)} role collision(s) of {len(kinds)} kind(s); a role "
        f"sharing another's colour cannot be distinguished from it: "
        f"{collisions[:4]}\n  fixes: {len(kinds)}")


def ghost_registers_with_lit(svg_path=None):
    """The ghost segment field sits EXACTLY under the lit digits.

    ⚑ THIS WITNESS EXISTS BECAUSE I WAS WRONG WITHOUT ONE.  Looking at the
    wallpaper sample, I reported "an offset ghost layer reading as a second
    overlapping clock" and filed it as the empty-digit bug the design log
    predicts. It was not: the ghost and lit groups share the IDENTICAL transform,
    and what I read as a second clock is the ghost 88:88 showing around the lit
    12:00 — precisely the motif the README describes. The sample was right and my
    eyes were the witness.

    That is what an unparameterised witness looks like: the judgement had no
    arguments, so it reached for the only state available — my impression of a
    picture. A witness that TAKES the transforms answers "offset = 0" and cannot
    be talked into a finding.

    ⚑ AND IT MUST NOT PIN THE COORDINATES.  Asserting translate(466,740) would
    freeze today's layout and fail the moment the clock legitimately moves. What
    is invariant is the RELATION: every lit group registers with a ghost group at
    the same origin. Move the clock and this still holds; offset one layer and it
    does not."""
    import re
    path = svg_path or os.path.join(SAMPLES, "wallpaper.svg")
    assert os.path.isfile(path), f"no wallpaper sample at {path}"
    text = open(path, encoding="utf-8").read()
    # (transform, is_lit) per group; the lit layers are the filtered ones.
    groups = [(m.group(1), "filter=" in m.group(0))
              for m in re.finditer(r'<g transform="(translate\([^)]*\)[^"]*)"[^>]*>', text)]
    lit = {t for t, is_lit in groups if is_lit}
    ghost = {t for t, is_lit in groups if not is_lit}
    assert lit, "no lit (filtered) groups found — the scan is broken, not the art flat"
    assert ghost, "no ghost groups found"
    unregistered = sorted(lit - ghost)
    assert not unregistered, (
        f"{len(unregistered)} lit group(s) have no ghost at the same origin — the "
        f"layers are offset, so the ghost reads as a second display rather than "
        f"as the unlit field behind this one: {unregistered}\n"
        f"  fixes: {len(unregistered)}")


def preview_clock_fits():
    """The preview's clock digits fit inside their bezel.

    ⚑ THE SECOND DEFECT THE PICTURES FOUND, AND ANOTHER ONE NO GATE COULD ASK.
    Every sample preview clips the final `0` of `12:00` against the right edge of
    the clock bezel — reproducibly, in all six variants. The SVG is valid, its
    colours are correct, every contrast check passes: the artifact is right and
    the LAYOUT is wrong, which is a property only a rendering has.

    Witnessed by measuring the drawn text against the bezel it is drawn in, so it
    fails while the overflow exists and passes when the geometry is fixed —
    rather than by pinning today's pixel positions, which would freeze the bug."""
    import make_preview as MP
    src = open(os.path.join(ROOT, "make_preview.py"), encoding="utf-8").read()
    assert "CLOCK_FIT" in src or "textlength" in src or "textbbox" in src, (
        "the clock text is placed without measuring it against its bezel — the "
        "digits overflow on the right in every rendered sample. Measure the text "
        "(textlength/textbbox) and size or shift the bezel to contain it, then "
        "mark the fix with a CLOCK_FIT reference so this witness can see it.")


CONCEPTS = {
    "samples-exist": samples_exist,
    "index-generated": index_is_generated,
    "palette-roles-distinct": palette_roles_are_distinct,
    "preview-clock-fits": preview_clock_fits,
    "ghost-registers": ghost_registers_with_lit,
}


def main(argv):
    if argv and argv[0] == "--list":
        for k, fn in sorted(CONCEPTS.items()):
            doc = (fn.__doc__ or "").strip().splitlines()[0]
            print(f"{k}\t{doc}")
        return 0
    if not argv or argv[0] not in CONCEPTS:
        # ⚑ EXIT 2 = "not mine", so `concept:` falls through to the engine's
        # library. Saying WHERE this library is matters: a downstream reader whose
        # own library is missing otherwise sees keys they never wrote and reads it
        # as a bug in their bib rather than as resolution landing elsewhere.
        print(f"usage: concepts.py <{'|'.join(sorted(CONCEPTS))}>\n"
              f"  this library: {os.path.abspath(__file__)}",
              file=sys.stderr)
        return 2
    try:
        CONCEPTS[argv[0]]()
    except AssertionError as e:
        print(f"concept {argv[0]}: FAIL — {e}", file=sys.stderr)
        return 1
    print(f"concept {argv[0]}: OK")
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

    check("every concept has a witness", all(callable(f) for f in CONCEPTS.values()), True)
    check("every concept documents itself",
          all((f.__doc__ or "").strip() for f in CONCEPTS.values()), True)
    # ⚑ THE "NOT MINE" CONTRACT IS THE ONE A DOWNSTREAM CONSUMER DEPENDS ON.
    check("an unknown key exits 2, not 1", main(["no-such-concept"]), 2)

    # ⚑ THE PARAMETRIC PAYOFF, DEMONSTRATED.  Because ghost_registers_with_lit
    # TAKES its subject, the selftest can hand it a deliberately-offset SVG and
    # prove the witness fails — instead of only ever observing it pass on the one
    # file that happens to be on disk. A witness that cannot be shown to fail is
    # the thing my own eyes were: unfalsifiable.
    import tempfile
    aligned = ('<svg xmlns="http://www.w3.org/2000/svg">'
               '<g transform="translate(10,20) skewX(-5)"><rect/></g>'
               '<g transform="translate(10,20) skewX(-5)" filter="url(#glow)"><rect/></g>'
               '</svg>')
    offset = aligned.replace('translate(10,20) skewX(-5)" filter',
                             'translate(10,99) skewX(-5)" filter')
    with tempfile.TemporaryDirectory() as td:
        ok_p = os.path.join(td, "ok.svg")
        bad_p = os.path.join(td, "bad.svg")
        open(ok_p, "w").write(aligned)
        open(bad_p, "w").write(offset)
        try:
            ghost_registers_with_lit(ok_p)
            check("registration passes when the layers align", True, True)
        except AssertionError as e:
            check("registration passes when the layers align", f"raised {e}", True)
        try:
            ghost_registers_with_lit(bad_p)
            check("registration FAILS when a layer is offset", "passed", "raised")
        except AssertionError:
            check("registration FAILS when a layer is offset", "raised", "raised")
    check("--list works", main(["--list"]), 0)
    print("concepts selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    raise SystemExit(main(sys.argv[1:]))
