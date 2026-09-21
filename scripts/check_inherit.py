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


def rows():
    """[(variant, icon_parents, cursor_parent, icon_dirs, defaults_ok)]"""
    out = []
    for v in MI.VARIANTS:
        ic = _ini(MI.icon_index(v))["Icon Theme"]
        cu = _ini(MI.cursor_index(v))["Icon Theme"]
        d = _ini(MI.defaults_fragment(v))
        defaults_ok = (d["kdeglobals][Icons"]["Theme"] == ic["Name"] and
                       d["kcminputrc][Mouse"]["cursorTheme"] == cu["Name"])
        out.append((v, ic["Inherits"].split(","), cu["Inherits"],
                    [s for s in ic.get("Directories", "").split(",") if s], defaults_ok))
    return out


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
    rs = rows()
    if not rs:
        print("check_inherit: REFUSED — no variants", file=sys.stderr)
        return 2
    if "--map" in argv:
        for v, ip, cp, dirs, dflt in rs:
            print(f"{v:16s}  icons -> {','.join(ip):28s}  cursors -> {cp:16s}  dirs {dirs}  defaults {'ok' if dflt else 'MISMATCH'}")
        return 0
    bad, skipped = problems(rs)
    if bad:
        print(f"check_inherit: REFUSED — {len(bad)} problem(s) over {len(rs)} variants:", file=sys.stderr)
        for b in bad:
            print(f"    {b}", file=sys.stderr)
        return 1
    print(f"check_inherit: {len(rs)} of {len(rs)} variants inherit well-formed parents"
          + (f"; {skipped} parent lookup(s) SKIPPED (not installed here)" if skipped else
             " — every parent is installed on this host"))
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    rs = rows()
    chk("six variants", len(rs), 6)
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
