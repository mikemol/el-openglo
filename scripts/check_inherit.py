#!/usr/bin/env python3
"""check_inherit.py — the inheriting icon and cursor themes name parents that exist.

⚑ WHAT IS CHECKED.  make_inherit emits, per variant, an icon theme that draws
nothing (Breeze recoloured by the scheme through FollowsColorScheme) and a
cursor theme that draws nothing (Breeze cursors by Inherits). A theme like
that is only as real as its parent: an `Inherits=` naming a theme the host
does not have is a blank desktop, silently. So this reads each emitted
index.theme back as INI, and asks (a) is the parent chain well-formed (hicolor
last for icons, one parent for cursors), (b) does the icon theme declare a
directory (KIconTheme rejects one that does not), (c) does the LnF defaults
fragment select exactly these names, and (d) does every parent EXIST under
/usr/share/icons on this host — a SKIP, counted, when Breeze is not installed.

    scripts/check_inherit.py            # exit 0 iff every parent resolves (or SKIP)
    scripts/check_inherit.py --map      # variant -> icon parents / cursor parent
    scripts/check_inherit.py --selftest
"""
import configparser
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import make_inherit as MI                                        # noqa: E402

ICON_ROOTS = ("/usr/share/icons", "/usr/local/share/icons")


def _ini(text):
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str
    cp.read_string(text)
    return cp


def variants():
    """The variant ids this tree DECLARES, from the palette authority (make_schemes.GRID).

    ⚑ NOT make_inherit.VARIANTS (W65, 2026-09-22). That tuple is the EMITTER's own
    typed roster, and iterating it made the check measure whatever the emitter
    chose to emit: dropping one variant took "6 of 6" to "5 of 5", exit 0
    (check_discriminates, probe inherit/variant-roster). The emitter's roster is
    now a thing MEASURED against the authority, not the population itself.
    Read through scripts/variant_roster.py (W61 B2): one roster, one reader."""
    import variant_roster
    return variant_roster.ids()


def rows():
    """([(variant, icon_parents, cursor_parent, icon_dirs, defaults_ok)], [(variant, why)]).

    ⚑ EVERY UNMEASURABLE MEMBER IS RETURNED WITH A REASON, never skipped: a
    declared variant make_inherit does not emit, one it emits that the palette
    does not declare, or one whose index.theme does not parse."""
    out, missing = [], []
    declared, emitted = variants(), set(MI.VARIANTS)
    missing += [(v, "make_inherit emits it but the palette authority does not declare it")
                for v in sorted(emitted - set(declared))]
    for v in declared:
        if v not in emitted:
            missing.append((v, "declared by make_schemes.GRID but make_inherit.VARIANTS does not emit it"))
            continue
        try:
            ic = _ini(MI.icon_index(v))["Icon Theme"]
            cu = _ini(MI.cursor_index(v))["Icon Theme"]
            d = _ini(MI.defaults_fragment(v))
            defaults_ok = (d["kdeglobals][Icons"]["Theme"] == ic["Name"] and
                           d["kcminputrc][Mouse"]["cursorTheme"] == cu["Name"])
            out.append((v, ic["Inherits"].split(","), cu["Inherits"],
                        [s for s in ic.get("Directories", "").split(",") if s], defaults_ok))
        except (KeyError, configparser.Error) as e:
            missing.append((v, f"an emitted index/fragment does not parse: {type(e).__name__}: {e}"))
    return out, missing


def parent_exists(name, roots=ICON_ROOTS):
    return any(os.path.isfile(os.path.join(r, name, "index.theme")) for r in roots)


def problems(rs, roots=ICON_ROOTS):
    bad, skipped = [], 0
    for v, ip, cp, dirs, dflt in rs:
        if not ip or ip[-1] != "hicolor":
            bad.append(f"{v}: icon Inherits does not end in hicolor ({ip})")
        if not dirs:
            bad.append(f"{v}: the icon theme declares no Directories (KIconTheme rejects it)")
        if not cp:
            bad.append(f"{v}: the cursor theme names no parent")
        if not dflt:
            bad.append(f"{v}: the LnF defaults do not select the emitted theme names")
        for p in ip[:-1] + [cp]:
            if not parent_exists(p, roots):
                skipped += 1
                print(f"check_inherit: SKIP — {v}: parent {p!r} is not installed here "
                      f"(a fact about this host)", file=sys.stderr)
    return bad, skipped


def main(argv):
    known = {"--map", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_inherit: unknown flag {a!r}", file=sys.stderr)
            return 2
    rs, missing = rows()
    if "--map" in argv:
        for v, ip, cp, dirs, dflt in rs:
            print(f"{v:16s}  icons -> {','.join(ip):28s}  cursors -> {cp:16s}  dirs {dirs}  defaults {'ok' if dflt else 'MISMATCH'}")
        for v, why in missing:
            print(f"{v:16s}  MISSING — {why}")
        return 0
    # ⚑ THE POPULATION IS ASSERTED BEFORE THE OUTCOME: expected is the palette
    # authority's roster, never a typed count. n of n is green for every n.
    expected = len(variants())
    if missing or len(rs) != expected or not rs:
        print(f"check_inherit: REFUSED — measured {len(rs)} of {expected} declared variant(s) "
              f"(make_schemes.GRID). A SHRINKING POPULATION IS NOT A PASSING ONE.",
              file=sys.stderr)
        for v, why in missing:
            print(f"    {v}: {why}", file=sys.stderr)
        return 2
    bad, skipped = problems(rs)
    if bad:
        print(f"check_inherit: REFUSED — {len(bad)} problem(s) over {len(rs)} variants:", file=sys.stderr)
        for b in bad:
            print(f"    {b}", file=sys.stderr)
        return 1
    print(f"check_inherit: {len(rs)} of {expected} declared variants inherit well-formed parents"
          + (f"; {skipped} parent lookup(s) SKIPPED (not installed here)" if skipped else
             " — every parent is installed on this host"))
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    rs, missing = rows()
    # ⚑ THE LIVENESS CONJUNCT (replaces a typed "six variants"): complete against
    # the authority, AND not vacuously complete.
    chk("the declared population is complete on a clean tree",
        (missing, len(rs) == len(variants())), ([], True))
    chk("and it is not vacuously complete", len(rs) > 0, True)
    saved = MI.VARIANTS
    try:
        MI.VARIANTS = saved[:-1]
        chk("an emitter roster short one variant is a missing member",
            [v for v, _w in rows()[1]], [saved[-1]])
        chk("...and main REFUSES", main(["x"]), 2)
    finally:
        MI.VARIANTS = saved
    chk("every icon chain ends in hicolor", all(r[1][-1] == "hicolor" for r in rs), True)
    chk("Off variants inherit breeze-dark, Lit inherit breeze",
        all((r[1][0] == "breeze") == r[0].endswith("-Lit") for r in rs), True)
    chk("cursors: dark ground gets light arrows, light ground gets dark arrows",
        all((r[2] == "breeze_cursors") == r[0].endswith("-Lit") for r in rs), True)
    chk("every icon theme declares a directory", all(r[3] for r in rs), True)
    chk("the defaults select the emitted names", all(r[4] for r in rs), True)
    chk("the emitted icon index parses as INI with FollowsColorScheme",
        _ini(MI.icon_index("EL-Azure"))["Icon Theme"]["FollowsColorScheme"], "true")
    # ⚑ THE CHECK MUST SEE A MISSING PARENT AND A BROKEN CHAIN (synthetic)
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        bad, skipped = problems(rs, roots=(td,))
        chk("an empty icon root SKIPs every parent lookup, counted", skipped, len(rs) * 3 - sum(1 for r in rs if len(r[1]) == 2))
        chk("...and is not a refusal", bad, [])
    broken = [("SYN", ["breeze"], "breeze_cursors", [], False)]
    bad, _s = problems(broken, roots=("/nonexistent",))
    chk("a chain without hicolor is seen", any("hicolor" in b for b in bad), True)
    chk("a theme without directories is seen", any("Directories" in b for b in bad), True)
    chk("defaults that do not select the theme are seen", any("defaults" in b for b in bad), True)
    print("check_inherit selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
