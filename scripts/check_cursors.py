#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_cursors.py — MEASURE the phosphor cursor themes (W36); policy/cursors.rego decides.

Per variant: make_cursors.render_all writes the theme into a temp dir (or --root
reads an already-staged usr/share/icons), and this reads every entry of its
cursors/ back through make_cursors.read_xcursor — which name is a file, which a
symlink and to what, which nominal sizes it carries, and the DOMINANT opaque
colours of its 32 px image (each colour covering >= DOMINANT_SHARE of the fully
opaque pixels). The variant's tokens (parse_scheme's phosphor + ground) ride along,
so the policy compares the emitted pixels against the solved palette.

    scripts/check_cursors.py --json            # the measurement, for opa_gate
    scripts/check_cursors.py --json --root DIR # measure a staged icons dir instead
    scripts/check_cursors.py                   # human summary, n of m
    scripts/check_cursors.py --selftest        # the measurement can SEE a wrong colour
    scripts/opa_gate.py cursors                # the gate

⚑ WEAKNESS, stated: the colour measurement is over DOMINANT colours, not every
pixel — antialiased edges blend rim, body and transparency, so a stray colour
covering a few pixels (a thin wrong-coloured detail) is invisible here. What it
does see is a glyph whose rim or body is not its variant's token, which is the
drift an emitter computing its own colours produces. It measures the files, not
what a cursor server shows: whether KDE/GTK actually PICK the theme is the LnF
defaults' job (make_inherit.defaults_fragment), not measured here.

A missing cairosvg/PIL is a SKIP (a `withheld` case), a fact about the host.
"""
import json
import os
import sys
import tempfile
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# the repo's prevailing convention for reaching the tree's modules (W62 retires it)
sys.path.insert(0, ROOT)

DOMINANT_SHARE = 0.15
PROBE_SIZE = 32
GHOST_TOL = 3       # per-channel slack when matching the ghost composite


def dominant(px, share=DOMINANT_SHARE):
    """['#rrggbb'] covering >= share of the fully opaque pixels, most common first."""
    opaque = Counter("#%06x" % (p & 0xFFFFFF) for p in px if (p >> 24) == 0xFF)
    total = sum(opaque.values())
    if not total:
        return []
    return [c for c, n in opaque.most_common() if n / total >= share]


def _hex(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5))


def ghost_rgb(tokens):
    """The ghost token composited at its solved alpha over the ground — the colour
    an unlit segment lands on in the pixels (a measurement of what is expected)."""
    a = float(tokens["ghost_alpha"])
    g, b = _hex(tokens["ghost"]), _hex(tokens["ground"])
    return tuple(round(a * x + (1 - a) * y) for x, y in zip(g, b))


def ghost_pixels(px, tokens, tol=GHOST_TOL):
    """How many fully opaque pixels sit within `tol` per channel of the ghost
    composite — the unlit segments, as drawn."""
    want = ghost_rgb(tokens)
    n = 0
    for p in px:
        if (p >> 24) == 0xFF and all(abs(((p >> s) & 255) - w) <= tol
                                     for s, w in zip((16, 8, 0), want)):
            n += 1
    return n


def measure_file(path, tokens=None):
    """`frames` is the probe-size animation: per frame its delay, its lit-token
    pixel count and its ghost pixel count (None when no tokens were given)."""
    import make_cursors as MC
    try:
        allf = MC.read_xcursor_frames(path)
    except (OSError, ValueError) as e:
        return {"readable": False, "error": str(e), "sizes": [], "dominant": [], "frames": []}
    probe = allf.get(PROBE_SIZE)
    frames = []
    for f in probe or []:
        px = f[4]
        lit = sum(1 for p in px if tokens and (p >> 24) == 0xFF
                  and "#%06x" % (p & 0xFFFFFF) == tokens["lit"]) if tokens else None
        frames.append({"delay": f[5], "lit_px": lit,
                       "ghost_px": ghost_pixels(px, tokens) if tokens else None,
                       "pixels": hash(tuple(px)) & 0xFFFFFFFF})
    return {"readable": True, "error": None, "sizes": sorted(allf),
            "frame_counts": {str(k): len(v) for k, v in sorted(allf.items())},
            "dominant": dominant(probe[0][4]) if probe else [], "frames": frames}


def measure_theme(tdir, variant):
    import make_cursors as MC
    cdir = os.path.join(tdir, "cursors")
    entries = {}
    toks = MC.tokens(variant)
    names = sorted(os.listdir(cdir)) if os.path.isdir(cdir) else []
    for n in names:
        p = os.path.join(cdir, n)
        e = measure_file(p, toks)
        e["link"] = os.readlink(p) if os.path.islink(p) else None
        entries[n] = e
    return {"id": variant, "theme": os.path.basename(tdir),
            "index_theme": os.path.isfile(os.path.join(tdir, "index.theme")),
            "tokens": toks, "entries": entries}


def roster_drift():
    """The emitters' own VARIANTS compared TO the roster (W61 R1): make_cursors renders
    its list, make_inherit names the theme per variant — either dropping one is a fact."""
    import make_cursors as MC
    import make_inherit as INH
    import variant_roster as VR
    return VR.drift_facts({"make_cursors": MC.VARIANTS, "make_inherit": INH.VARIANTS})


def measure(root=None):
    """The population is variant_roster.ids() — GRID's declaration, never an emitter's
    VARIANTS — so an emitter that drops a variant leaves a theme dir unmeasured-as-empty
    and a `roster_drift` fact, not a quietly shorter "n of n"."""
    import variant_roster as VR
    roster = VR.ids()
    try:
        import cairosvg  # noqa: F401
        import PIL  # noqa: F401
    except ImportError as e:
        return {"cases": [{"id": v, "withheld": f"cannot rasterise: {e}"} for v in roster],
                "roster_drift": roster_drift()}
    import make_cursors as MC
    import make_inherit as INH
    if root is None:
        tmp = tempfile.mkdtemp(prefix="el-cursors-")
        MC.render_all(MC.VARIANTS, tmp)
        root = tmp
    cases = []
    for v in roster:
        tdir = os.path.join(root, INH.cursor_theme_name(v))
        cases.append(measure_theme(tdir, v))
    return {"probe_size": PROBE_SIZE, "dominant_share": DOMINANT_SHARE, "cases": cases,
            "roster_drift": roster_drift()}


def _selftest():
    ok = True

    def see(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        ok = ok and cond

    try:
        import make_cursors as MC
        import cairosvg  # noqa: F401
    except ImportError as e:
        print(f"  SKIP — cannot rasterise ({e})\ncheck_cursors selftest: SKIP")
        return True
    v = "EL-Openglo"
    t = MC.tokens(v)
    with tempfile.TemporaryDirectory() as d:
        good = os.path.join(d, "default")
        open(good, "wb").write(MC.cursor_file("default", v))
        bad = os.path.join(d, "bad")
        open(bad, "wb").write(MC.cursor_file("default", v, colours={"lit": "#ff0000", "ground": t["ground"]}))
        open(os.path.join(d, "junk"), "wb").write(b"not a cursor")
        g, b, j = measure_file(good), measure_file(bad), measure_file(os.path.join(d, "junk"))
        see(f"the emitted glyph's dominant colours are its tokens ({g['dominant']})",
            bool(g["dominant"]) and set(g["dominant"]) <= {t["lit"], t["ground"]})
        see(f"a wrong-colour fixture is SEEN: #ff0000 among {b['dominant']}", "#ff0000" in b["dominant"])
        see(f"every size is read back ({g['sizes']})", g["sizes"] == list(MC.SIZES))
        see("a non-XCursor file is unreadable, not silently empty", j["readable"] is False)
        wf = os.path.join(d, "wait")
        open(wf, "wb").write(MC.cursor_file("wait", v))
        w = measure_file(wf, t)
        see(f"wait carries {MC.SEGS} frames per size ({w['frame_counts']})",
            set(w["frame_counts"].values()) == {MC.SEGS} and len(w["frame_counts"]) == len(MC.SIZES))
        see(f"every wait frame has delay {MC.FRAME_MS} ms and the frames differ",
            {f["delay"] for f in w["frames"]} == {MC.FRAME_MS}
            and len({f["pixels"] for f in w["frames"]}) == MC.SEGS)
        see(f"every wait frame shows lit AND ghost ink ({[(f['lit_px'], f['ghost_px']) for f in w['frames']]})",
            all(f["lit_px"] > 0 and f["ghost_px"] > 0 for f in w["frames"]))
        open(wf, "wb").write(MC.cursor_file("wait", v, colours={"ghost": "#ff00ff"}))
        wb = measure_file(wf, t)
        see(f"a wrong-coloured ghost is SEEN (ghost px {[f['ghost_px'] for f in wb['frames']]} "
            f"vs {[f['ghost_px'] for f in w['frames']]})",
            max(f["ghost_px"] for f in wb["frames"]) * 4 < min(f["ghost_px"] for f in w["frames"]))
        see("a static glyph is one frame with no delay",
            [f["delay"] for f in g["frames"]] == [0] if g.get("frames") is not None else False)
    import make_inherit as INH
    see(f"the live emitters agree with the roster ({roster_drift()})", roster_drift() == [])
    kept = INH.VARIANTS
    try:
        INH.VARIANTS = [x for x in kept if x != "EL-Amber"]     # a planted drop
        dropped = roster_drift()
    finally:
        INH.VARIANTS = kept
    see(f"an emitter that drops a variant is SEEN ({dropped})",
        [(d["who"], d["variant"]) for d in dropped] == [("make_inherit", "EL-Amber")])
    print("check_cursors selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    known = {"--json", "--selftest", "--root"}
    args = argv[1:]
    for a in args:
        if a.startswith("--") and a not in known:
            print(f"check_cursors: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in args:
        return 0 if _selftest() else 1
    root = None
    if "--root" in args:
        i = args.index("--root")
        if i + 1 >= len(args):
            print("check_cursors: --root needs a directory", file=sys.stderr)
            return 2
        root = os.path.abspath(args[i + 1])
    doc = measure(root)
    if "--json" in args:
        print(json.dumps(doc))
        return 0
    cases = doc["cases"]
    measured = [c for c in cases if "withheld" not in c]
    for c in cases:
        if "withheld" in c:
            print(f"  SKIP {c['id']}: {c['withheld']}")
            continue
        files = sum(1 for e in c["entries"].values() if e["link"] is None)
        links = len(c["entries"]) - files
        tok = {c["tokens"]["lit"], c["tokens"]["ground"]}
        off = {n: sorted(set(e["dominant"]) - tok) for n, e in c["entries"].items()
               if e["link"] is None and set(e["dominant"]) - tok}
        print(f"  {c['theme']:24s} {files} glyphs + {links} aliases; "
              f"off-token glyphs: {off or 'none'}")
    for d in doc.get("roster_drift", []):
        print(f"  DRIFT {d['variant']}: {d['why']}")
    print(f"check_cursors: {len(measured)} of {len(cases)} variant(s) measured "
          f"(the verdict is policy/cursors.rego: scripts/opa_gate.py cursors)")
    return 0 if measured else 3


if __name__ == "__main__":
    sys.exit(main(sys.argv))
