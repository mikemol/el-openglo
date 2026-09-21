#!/usr/bin/env python3
"""check_template_parity.py — an extracted template still emits the same bytes.

⚑ EXTRACTION MUST BE OUTPUT-NEUTRAL, AND SAYING SO IS NOT SHOWING IT.  Moving a
104-line QML document out of an f-string means re-typing ~40 doubled brace pairs
as single ones and turning four `{name}` holes into `$name`. Every one of those
is a chance to drop a character in a way that still parses, still lints, and
renders subtly different markup. The generator's OUTPUT is the invariant.

    scripts/check_template_parity.py            # every declared pair agrees
    scripts/check_template_parity.py --pairs    # what is compared against what

⚑ THE COMPARISON IS AGAINST A RECORDED BASELINE, NOT AGAINST THE OLD LITERAL.
Keeping the pre-extraction literal in the source to diff against would defeat the
purpose — the artifact would still be embedded. So the baseline is a file written
BEFORE the rewrite, and this asserts the generator still reproduces it.

⚑ A MISSING BASELINE IS A REFUSAL, NOT A PASS.  An absent baseline means nobody
captured the before-state, so parity is unverified rather than confirmed.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINES = os.path.join(ROOT, "catalog", "baselines")

# (module, accessor, args, baseline filename). `args` names a callable in the
# module that supplies the argument, so a generator taking a token dict can be
# exercised without this file knowing what a token dict is.
PAIRS = (
    ("make_segment_display", "segment_char_component", None, "SegmentChar.qml"),
    ("make_clock", "CONFIG_XML", None, "clock-config.kcfg"),
    ("make_clock", "CONFIG_QML", None, "clock-config.qml"),
    ("make_wallpaper_live", "config_main_xml", None, "live-wallpaper-config.kcfg"),
    # ⚑ A PER-VARIANT SURFACE IS PINNED AT ONE VARIANT, and that is enough: the
    # holes are filled from the same call either way, so a transcription error in
    # the 88 lines AROUND them shows up here regardless of which variant is used.
    # ⚑ THE MARQUEE'S BYTES DEPEND ON A BUILD-TIME FONT since ⊕MATRIX-FONT-INPUT
    # (s77): the Latin-1 extension is rasterised from it. The pair pins the font
    # by ABSOLUTE PATH (make_notify_marquee.PARITY_FONT); a host without that
    # file SKIPs this pair — printed, counted — rather than reporting a host
    # difference as a template difference.
    ("make_notify_marquee", "main_qml", ("EL-Openglo", "PARITY_FONT"),
     "marquee-main-EL-Openglo.qml"),
    # the settings (W34 c): the kcfg carries the solved ghost alpha as its default
    ("make_notify_marquee", "config_xml", "EL-Openglo", "marquee-config-EL-Openglo.kcfg"),
    ("make_notify_marquee", "config_qml", None, "marquee-config.qml"),
    ("make_notify_marquee", "body_parser", None, "marquee-body.js"),
    # ⚑ THE GEOMETRY MOVED TOO, NOT ONLY THE MARKUP.  This surface's seven-seg map
    # and stroke table were hand-written inside the f-string; they are now
    # segment_topology's projection. So this pair proves TWO things at once — that
    # the 120 lines transcribed correctly, and that the substrate's tables are
    # byte-identical to the ones this file used to author.
    ("make_wallpaper_live", "main_qml", "EL-Openglo",
     "live-wallpaper-main-EL-Openglo.qml"),
    # four holes since W8: ground, lit, and the scheme's ghost + ghost_alpha
    ("make_deb", "_splash_qml", ('"#081411"', '"#4bfad7"', '"#2d8f7a"', "0.503"), "splash.qml"),
)


class _Skip(Exception):
    """A pair that cannot be evaluated on this host (a pinned file is absent)."""


def _value(module, accessor, argsrc):
    # ⚑ THE GENERATORS READ FILES BY BARE NAME, so the WORKING DIRECTORY is part
    # of their contract, not just sys.path. make_clock opens "make_wallpaper.py"
    # at import to pull the shared SEG/DIGIT tables; imported from anywhere else
    # that is a FileNotFoundError. The gate runs checks from the paperkit project
    # directory, so this passed standalone and failed under the gate — a
    # difference in cwd reported as a difference in output.
    os.chdir(ROOT)
    sys.path.insert(0, ROOT)
    import importlib
    mod = importlib.import_module(module)
    obj = getattr(mod, accessor)
    if not callable(obj):
        return obj
    if argsrc is None:
        return obj()

    def _one(token):
        # a module attribute when the argument cannot be spelled (a token dict);
        # otherwise the literal itself (a variant name, a colour)
        if hasattr(mod, token):
            v = getattr(mod, token)
            v = v() if callable(v) else v
            # an absolute path names a HOST FILE the pair depends on: absent, the
            # pair is unverifiable here, which is a SKIP and not a difference
            if isinstance(v, str) and v.startswith("/") and not os.path.isfile(v):
                raise _Skip(f"{token} = {v} is not on this host")
            return v
        return token

    # a tuple names several arguments; a bare string names one
    if isinstance(argsrc, tuple):
        return obj(*[_one(a) for a in argsrc])
    return obj(_one(argsrc))


def shared_inodes():
    """[(name, nlink)] for every baseline that is a HARD LINK to something else.

    ⚑ A BASELINE THAT SHARES AN INODE IS NOT A BASELINE.  Measured 2026-09-21:
    catalog/baselines/clock-config.qml had link count 8 — one inode with the
    TEMPLATE it certifies and six emitted copies — so editing the template
    silently edited its own baseline and @PARITY could not fail. A dedup pass
    over ~/github (jdupes -L / hardlink / rdfind) had merged every byte-identical
    file; capture_baseline writes plain files and never did this. The tool that
    owns the baselines is the one that must notice, because nothing else looks."""
    out = []
    for name in sorted(os.listdir(BASELINES)) if os.path.isdir(BASELINES) else []:
        p = os.path.join(BASELINES, name)
        if os.path.isfile(p) and os.stat(p).st_nlink > 1:
            out.append((name, os.stat(p).st_nlink))
    return out


def unlink_shared():
    """Give every shared-inode baseline its own inode (same bytes, same mode)."""
    import shutil
    done = []
    for name, n in shared_inodes():
        p = os.path.join(BASELINES, name)
        tmp = p + ".unlink"
        shutil.copy2(p, tmp)
        os.replace(tmp, p)               # a new inode under the old name
        done.append((name, n))
    return done


def compare():
    """[(label, verdict)] for every declared pair."""
    out = []
    for module, accessor, argsrc, name in PAIRS:
        label = f"{module}.{accessor}"
        path = os.path.join(BASELINES, name)
        if not os.path.isfile(path):
            out.append((label, f"NO BASELINE ({name})"))
            continue
        if os.stat(path).st_nlink > 1:
            out.append((label, f"SHARED INODE ({name}: {os.stat(path).st_nlink} links) — "
                               f"not an independent record; run --unlink"))
            continue
        try:
            got = _value(module, accessor, argsrc)
        except _Skip as e:
            out.append((label, f"SKIP ({e})"))
            continue
        except Exception as e:                   # noqa: BLE001
            out.append((label, f"RAISED {type(e).__name__}: {e}"))
            continue
        want = open(path, encoding="utf-8").read()
        out.append((label, "ok" if got == want
                    else f"DIFFERS ({len(got)} vs {len(want)} bytes)"))
    return out


def diff(match):
    """The unified diff for the pair(s) whose label contains `match`.

    ⚑ "DIFFERS (6065 vs 5746 bytes)" NAMES THAT SOMETHING CHANGED AND NOT WHAT.
    Answering "what changed" then happens in the turn — a shell diff against a
    regenerated file — which is the judgement living outside a program. The pair
    is declared HERE, so the comparison belongs here too."""
    import difflib
    shown = 0
    for module, accessor, argsrc, name in PAIRS:
        label = f"{module}.{accessor}"
        if match not in label and match not in name:
            continue
        shown += 1
        path = os.path.join(BASELINES, name)
        if not os.path.isfile(path):
            print(f"{label}: NO BASELINE ({name})")
            continue
        want = open(path, encoding="utf-8").read()
        try:
            got = _value(module, accessor, argsrc)
        except Exception as e:                   # noqa: BLE001
            print(f"{label}: RAISED {type(e).__name__}: {e}")
            continue
        if got == want:
            print(f"{label}: ok (byte-identical)")
            continue
        for line in difflib.unified_diff(
                want.splitlines(), got.splitlines(),
                fromfile=f"baseline/{name}", tofile=f"{label}()", lineterm="", n=2):
            print(line)
    print(f"diff: {shown} of {len(PAIRS)} pair(s) matched {match!r}")
    return 0 if shown else 2


def main(argv):
    known = {"--pairs", "--diff", "--unlink", "--links"}
    flags = [a for a in argv[1:] if a.startswith("--")]
    for a in flags:
        if a not in known:
            print(f"check_template_parity: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--links" in argv:
        shared = shared_inodes()
        for name, n in shared:
            print(f"{n}\t{name}")
        print(f"links: {len(shared)} baseline(s) share an inode")
        return 0
    if "--unlink" in argv:
        done = unlink_shared()
        for name, n in done:
            print(f"unlinked {name} (was {n} links)")
        print(f"unlink: {len(done)} baseline(s) given their own inode")
        return 0
    if "--diff" in argv:
        rest = [a for a in argv[1:] if not a.startswith("--")]
        if not rest:
            print("check_template_parity: --diff needs a pair to match "
                  "(a module, accessor or baseline name)", file=sys.stderr)
            return 2
        return diff(rest[0])
    if "--pairs" in argv:
        for module, accessor, argsrc, name in PAIRS:
            print(f"{module}.{accessor}\t<-> catalog/baselines/{name}")
        return 0
    results = compare()
    if not results:
        print("check_template_parity: REFUSED — no pairs declared; the check is "
              "vacuous, not the templates faithful", file=sys.stderr)
        return 2
    skipped = [(l, v) for l, v in results if v.startswith("SKIP")]
    bad = [(l, v) for l, v in results if v != "ok" and not v.startswith("SKIP")]
    for label, verdict in skipped:
        print(f"check_template_parity: {label}: {verdict}", file=sys.stderr)
    if bad:
        print(f"check_template_parity: REFUSED — {len(bad)} of {len(results)} "
              f"template(s) no longer emit their baseline:", file=sys.stderr)
        for label, verdict in bad:
            print(f"    {label}: {verdict}", file=sys.stderr)
        print(f"  fixes: {len(bad)}", file=sys.stderr)
        return 1
    n = len(results) - len(skipped)
    print(f"check_template_parity: {n} of {len(results)} templates "
          f"emit their baseline byte-for-byte" + (f"; {len(skipped)} SKIPPED" if skipped else ""))
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

    check("pairs are declared", len(PAIRS) > 0, True)
    check("every pair names a baseline", all(p[3] for p in PAIRS), True)
    # ⚑ A MISSING BASELINE MUST NOT READ AS AGREEMENT.
    saved = globals()["BASELINES"]
    try:
        globals()["BASELINES"] = "/nonexistent"
        verdicts = {v for _l, v in compare()}
        check("a missing baseline is not 'ok'", "ok" in verdicts, False)
    finally:
        globals()["BASELINES"] = saved
    # ⚑ A SHARED INODE MUST BE SEEN, AND --unlink MUST END IT.  Plant a baseline
    # dir where one file is a hard link of another, in a tempdir.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        a = os.path.join(td, "a.txt")
        open(a, "w").write("same bytes\n")
        os.link(a, os.path.join(td, "b.txt"))
        try:
            globals()["BASELINES"] = td
            check("a hard-linked baseline is seen", [n for n, _ in shared_inodes()],
                  ["a.txt", "b.txt"])
            unlink_shared()
            check("--unlink leaves every baseline on its own inode", shared_inodes(), [])
            check("...with the same bytes", open(os.path.join(td, "b.txt")).read(),
                  "same bytes\n")
        finally:
            globals()["BASELINES"] = saved
    check("the real baselines share no inode", shared_inodes(), [])
    # ⚑ A PINNED HOST FILE THAT IS ABSENT IS A SKIP, NOT A DIFFERENCE — and a
    # SKIP is never 'ok'. Point the marquee pair's font at a path that does not
    # exist and the verdict must say SKIP and name the attribute.
    sys.path.insert(0, ROOT)
    import make_notify_marquee as MM
    saved_font = MM.PARITY_FONT
    try:
        MM.PARITY_FONT = "/nonexistent/font.ttf"
        v = dict(compare()).get("make_notify_marquee.main_qml", "")
        check("an absent pinned font SKIPs the pair", v.startswith("SKIP") and "PARITY_FONT" in v, True)
    finally:
        MM.PARITY_FONT = saved_font
    print("check_template_parity selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
