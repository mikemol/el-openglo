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

    scripts/check_inherit.py            # the verdict, as opa_gate inherit decides it
    scripts/check_inherit.py --json     # the measurement policy/inherit.rego decides
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


def measure(roots=ICON_ROOTS):
    """The MEASUREMENT policy/inherit.rego decides (W50): the declared roster and
    one case per member — its icon parent chain, cursor parent, icon Directories,
    whether the LnF defaults select the emitted names, and which parents are
    installed under `roots` — or `missing` with the reason it could not be read.
    A parent not installed here is a fact about the HOST (the policy withholds);
    a chain without hicolor, no Directories, no cursor parent or mismatched
    defaults are defects by the policy's ruling, not here."""
    rs, missing = rows()
    cases = [{"id": v, "icon_parents": ip, "cursor_parent": cp, "icon_dirs": dirs,
              "defaults_ok": dflt, "missing": None,
              "installed": {p: parent_exists(p, roots) for p in ip[:-1] + [cp] if p}}
             for v, ip, cp, dirs, dflt in rs]
    cases += [{"id": v, "missing": why} for v, why in missing]
    return {"roster": list(variants()), "cases": cases}


def main(argv):
    known = {"--map", "--selftest", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_inherit: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        import json
        print(json.dumps(measure(), indent=1))
        return 0
    if "--map" in argv:
        rs, missing = rows()
        for v, ip, cp, dirs, dflt in rs:
            print(f"{v:16s}  icons -> {','.join(ip):28s}  cursors -> {cp:16s}  dirs {dirs}  defaults {'ok' if dflt else 'MISMATCH'}")
        for v, why in missing:
            print(f"{v:16s}  MISSING — {why}")
        return 0
    import opa_gate
    return opa_gate.gate("inherit")


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
            [c["id"] for c in measure()["cases"] if c["missing"]], [saved[-1]])
    finally:
        MI.VARIANTS = saved
    chk("the emitted icon index parses as INI with FollowsColorScheme",
        _ini(MI.icon_index("EL-Azure"))["Icon Theme"]["FollowsColorScheme"], "true")
    # ⚑ THE MEASUREMENT MUST SEE AN UNINSTALLED PARENT (synthetic: an empty root).
    # That it is WITHHELD, and that a broken chain / no Directories / mismatched
    # defaults are DENIED, is policy/inherit_test.rego's ruling (W50).
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        m = measure(roots=(td,))
        chk("an empty icon root measures every parent as not installed",
            [p for c in m["cases"] for p, ok in c["installed"].items() if ok], [])
    chk("the real host's parents are measured (the lookup is not vacuous)",
        sum(len(c["installed"]) for c in measure()["cases"]) > 0, True)
    print("check_inherit selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
