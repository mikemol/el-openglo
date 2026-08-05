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
    ("make_notify_marquee", "main_qml", "EL-Openglo",
     "marquee-main-EL-Openglo.qml"),
    ("make_deb", "_splash_qml", ('"#081411"', '"#4bfad7"'), "splash.qml"),
)


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
            return v() if callable(v) else v
        return token

    # a tuple names several arguments; a bare string names one
    if isinstance(argsrc, tuple):
        return obj(*[_one(a) for a in argsrc])
    return obj(_one(argsrc))


def compare():
    """[(label, verdict)] for every declared pair."""
    out = []
    for module, accessor, argsrc, name in PAIRS:
        label = f"{module}.{accessor}"
        path = os.path.join(BASELINES, name)
        if not os.path.isfile(path):
            out.append((label, f"NO BASELINE ({name})"))
            continue
        try:
            got = _value(module, accessor, argsrc)
        except Exception as e:                   # noqa: BLE001
            out.append((label, f"RAISED {type(e).__name__}: {e}"))
            continue
        want = open(path, encoding="utf-8").read()
        out.append((label, "ok" if got == want
                    else f"DIFFERS ({len(got)} vs {len(want)} bytes)"))
    return out


def main(argv):
    known = {"--pairs"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_template_parity: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--pairs" in argv:
        for module, accessor, argsrc, name in PAIRS:
            print(f"{module}.{accessor}\t<-> catalog/baselines/{name}")
        return 0
    results = compare()
    if not results:
        print("check_template_parity: REFUSED — no pairs declared; the check is "
              "vacuous, not the templates faithful", file=sys.stderr)
        return 2
    bad = [(l, v) for l, v in results if v != "ok"]
    if bad:
        print(f"check_template_parity: REFUSED — {len(bad)} of {len(results)} "
              f"template(s) no longer emit their baseline:", file=sys.stderr)
        for label, verdict in bad:
            print(f"    {label}: {verdict}", file=sys.stderr)
        print(f"  fixes: {len(bad)}", file=sys.stderr)
        return 1
    print(f"check_template_parity: {len(results)} of {len(results)} templates "
          f"emit their baseline byte-for-byte")
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
    print("check_template_parity selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
