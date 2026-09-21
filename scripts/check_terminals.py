#!/usr/bin/env python3
"""check_terminals.py — every terminal format carries the ONE ansi table, and parses as itself.

⚑ FIVE SERIALISERS OVER ONE TABLE CAN STILL DISAGREE.  A serialiser that maps
`bright` to the wrong key, drops `dim`, or swaps magenta/purple emits a valid
file with the wrong colours — and a terminal shows no error for that. So each
format is parsed WITH THE PARSER ITS CONSUMER USES (tomllib for Alacritty,
configparser for foot, json for Windows Terminal, a properties reader for
Termux, Konsole's INI groups), and the colours read back must equal
make_konsole.ansi_table(variant) — the 8 normal, 8 bright, ground and
foreground — for every variant.

    scripts/check_terminals.py           # exit 0 iff every format round-trips the table
    scripts/check_terminals.py --map     # per format: which table keys it carries
    scripts/check_terminals.py --selftest

WEAKNESS. This proves the file says what the table says. Whether a terminal
READS that key (e.g. Alacritty's `dim` bank is optional) is the consumer's
schema, checked here only by key name.
"""
import configparser
import json
import os
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORMATS = ("konsole", "alacritty", "foot", "windows-terminal", "termux")


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


def _expected(t):
    """The colours a format must carry, keyed by role: ground, foreground, n0..n7, b0..b7."""
    e = {"ground": _hex(t["ground"]), "foreground": _hex(t["foreground"])}
    for i in range(8):
        e[f"n{i}"] = _hex(t["normal"][i])
        e[f"b{i}"] = _hex(t["bright"][i])
    return e


def read_back(fmt, text):
    """{role: '#rrggbb'} as the consumer's parser sees it. Raises on a parse failure."""
    names = ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white")
    out = {}
    if fmt == "konsole":
        cp = configparser.ConfigParser(interpolation=None)
        cp.read_string(text)

        def col(sec):
            return "#%02x%02x%02x" % tuple(int(x) for x in cp[sec]["Color"].split(","))
        out["ground"], out["foreground"] = col("Background"), col("Foreground")
        for i in range(8):
            out[f"n{i}"], out[f"b{i}"] = col(f"Color{i}"), col(f"Color{i}Intense")
    elif fmt == "alacritty":
        d = tomllib.loads(text)["colors"]
        out["ground"], out["foreground"] = d["primary"]["background"], d["primary"]["foreground"]
        for i, n in enumerate(names):
            out[f"n{i}"], out[f"b{i}"] = d["normal"][n], d["bright"][n]
    elif fmt == "foot":
        cp = configparser.ConfigParser(interpolation=None)
        cp.read_string(text)
        c = cp["colors"]
        out["ground"], out["foreground"] = "#" + c["background"], "#" + c["foreground"]
        for i in range(8):
            out[f"n{i}"], out[f"b{i}"] = "#" + c[f"regular{i}"], "#" + c[f"bright{i}"]
    elif fmt == "windows-terminal":
        d = json.loads(text)
        wt = ("black", "red", "green", "yellow", "blue", "purple", "cyan", "white")
        out["ground"], out["foreground"] = d["background"], d["foreground"]
        for i, n in enumerate(wt):
            out[f"n{i}"], out[f"b{i}"] = d[n], d["bright" + n.capitalize()]
    elif fmt == "termux":
        kv = dict(line.split("=", 1) for line in text.splitlines()
                  if line and not line.startswith("#"))
        out["ground"], out["foreground"] = kv["background"], kv["foreground"]
        for i in range(8):
            out[f"n{i}"], out[f"b{i}"] = kv[f"color{i}"], kv[f"color{i + 8}"]
    else:
        raise ValueError(f"unknown format {fmt!r}")
    return out


def emit(fmt, variant):
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_konsole as K
    return {"konsole": K.colorscheme, "alacritty": K.alacritty_toml, "foot": K.foot_ini,
            "windows-terminal": K.windows_terminal_json,
            "termux": K.termux_properties}[fmt](variant)


def compare(fmt, variant, text=None):
    """[(role, expected, got)] mismatches for one format/variant; [] when faithful."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_konsole as K
    exp = _expected(K.ansi_table(variant))
    got = read_back(fmt, text if text is not None else emit(fmt, variant))
    return [(k, exp[k], got.get(k)) for k in exp if got.get(k) != exp[k]]


def main(argv):
    known = {"--map"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_terminals: unknown flag {a!r}", file=sys.stderr)
            return 2
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_konsole as K
    variants = ["EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit", "EL-Amber", "EL-Amber-Lit"]
    if "--map" in argv:
        for fmt in FORMATS:
            got = read_back(fmt, emit(fmt, "EL-Openglo"))
            print(f"{fmt:17} {len(got)} roles: {' '.join(sorted(got))}")
        return 0
    bad, n = [], 0
    for v in variants:
        for fmt in FORMATS:
            n += 1
            try:
                mm = compare(fmt, v)
            except Exception as e:                       # noqa: BLE001
                bad.append(f"{fmt} {v}: does not parse as {fmt}: {type(e).__name__}: {e}")
                continue
            if mm:
                bad.append(f"{fmt} {v}: {len(mm)} role(s) differ from ansi_table: "
                           + ", ".join(f"{r} {e}!={g}" for r, e, g in mm[:3]))
    if not n:
        print("check_terminals: REFUSED — no variants; nothing measured", file=sys.stderr)
        return 2
    if bad:
        print(f"check_terminals: REFUSED — {len(bad)} of {n} emissions do not carry the table:",
              file=sys.stderr)
        for b in bad:
            print(f"    {b}", file=sys.stderr)
        return 1
    print(f"check_terminals: {n} of {n} emissions ({len(FORMATS)} formats x {len(variants)} variants) "
          f"parse as their consumer reads them and carry the one ansi table")
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

    for fmt in FORMATS:
        check(f"{fmt} emission is faithful", compare(fmt, "EL-Openglo"), [])
    # ⚑ EACH READER MUST SEE A SWAPPED COLOUR — plant one in every format.
    good = emit("alacritty", "EL-Openglo")
    swapped = good.replace('red = "', 'red = "#ff00ff" # ', 1)
    check("alacritty: a swapped colour is seen", compare("alacritty", "EL-Openglo", swapped) != [], True)
    good = emit("windows-terminal", "EL-Openglo")
    d = json.loads(good)
    d["brightRed"], d["brightGreen"] = d["brightGreen"], d["brightRed"]
    check("windows-terminal: swapped brights are seen",
          compare("windows-terminal", "EL-Openglo", json.dumps(d)) != [], True)
    good = emit("foot", "EL-Openglo")
    check("foot: a dropped key is a parse failure", _raises(lambda: compare(
        "foot", "EL-Openglo", good.replace("regular3=", "regular3x="))), True)
    good = emit("termux", "EL-Openglo")
    check("termux: a swapped colour is seen", compare(
        "termux", "EL-Openglo", good.replace("color1=", "color1=#000000 ")) != [], True)
    good = emit("konsole", "EL-Openglo")
    # the original value line becomes a comment; the planted one is read
    check("konsole: a changed Intense bank is seen", compare(
        "konsole", "EL-Openglo", good.replace("[Color1Intense]\nColor=", "[Color1Intense]\nColor=0,0,0\n#")) != [],
          True)
    check("a malformed TOML does not pass", _raises(lambda: compare("alacritty", "EL-Openglo", "[colors\n")), True)
    print("check_terminals selftest:", "PASS" if ok else "FAIL")
    return ok


def _raises(fn):
    try:
        fn()
        return False
    except Exception:                                    # noqa: BLE001
        return True


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
