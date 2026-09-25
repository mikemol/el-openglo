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

    scripts/check_terminals.py           # the verdict, as opa_gate terminals decides it
    scripts/check_terminals.py --json    # the measurement policy/terminals.rego decides
    scripts/check_terminals.py --map     # per format: which table keys it carries
    scripts/check_terminals.py --selftest

⚑ THE POPULATION IS DECLARED, NOT TYPED HERE (W65, 2026-09-22). It is the
product of two authorities: the variant roster (make_schemes.GRID — one scheme
per entry) and the format roster the EMITTER declares (make_konsole.
TERMINAL_FORMATS). It used to be two literals in this file, and dropping one
format took "30 of 30" to "24 of 24" — exit 0 both times (measured by
check_discriminates, probe terminals/typed-formats). The check's own READERS
are held against the emitter's roster in BOTH directions: a format emitted
with no reader, or a reader for a format no longer emitted, is a missing
member with a reason, and the check REFUSES before judging any colour.

WEAKNESS. This proves the file says what the table says. Whether a terminal
READS that key (e.g. Alacritty's `dim` bank is optional) is the consumer's
schema, checked here only by key name. And the roster is only as complete as
make_konsole's declaration: a sixth target nobody declares is not seen.
"""
import configparser
import json
import os
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

NAMES = ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white")


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


def _expected(t):
    """The colours a format must carry, keyed by role: ground, foreground, n0..n7, b0..b7."""
    e = {"ground": _hex(t["ground"]), "foreground": _hex(t["foreground"])}
    for i in range(8):
        e[f"n{i}"] = _hex(t["normal"][i])
        e[f"b{i}"] = _hex(t["bright"][i])
    return e


def _read_konsole(text):
    cp = configparser.ConfigParser(interpolation=None)
    cp.read_string(text)

    def col(sec):
        return "#%02x%02x%02x" % tuple(int(x) for x in cp[sec]["Color"].split(","))
    out = {"ground": col("Background"), "foreground": col("Foreground")}
    for i in range(8):
        out[f"n{i}"], out[f"b{i}"] = col(f"Color{i}"), col(f"Color{i}Intense")
    return out


def _read_alacritty(text):
    d = tomllib.loads(text)["colors"]
    out = {"ground": d["primary"]["background"], "foreground": d["primary"]["foreground"]}
    for i, n in enumerate(NAMES):
        out[f"n{i}"], out[f"b{i}"] = d["normal"][n], d["bright"][n]
    return out


def _read_foot(text):
    cp = configparser.ConfigParser(interpolation=None)
    cp.read_string(text)
    c = cp["colors"]
    out = {"ground": "#" + c["background"], "foreground": "#" + c["foreground"]}
    for i in range(8):
        out[f"n{i}"], out[f"b{i}"] = "#" + c[f"regular{i}"], "#" + c[f"bright{i}"]
    return out


def _read_windows_terminal(text):
    d = json.loads(text)
    wt = ("black", "red", "green", "yellow", "blue", "purple", "cyan", "white")
    out = {"ground": d["background"], "foreground": d["foreground"]}
    for i, n in enumerate(wt):
        out[f"n{i}"], out[f"b{i}"] = d[n], d["bright" + n.capitalize()]
    return out


def _read_termux(text):
    kv = dict(line.split("=", 1) for line in text.splitlines()
              if line and not line.startswith("#"))
    out = {"ground": kv["background"], "foreground": kv["foreground"]}
    for i in range(8):
        out[f"n{i}"], out[f"b{i}"] = kv[f"color{i}"], kv[f"color{i + 8}"]
    return out


# The CHECK's roster: which formats it knows how to read as the consumer does.
# Held against make_konsole.TERMINAL_FORMATS by drift(), never trusted alone.
READERS = {
    "konsole": _read_konsole,
    "alacritty": _read_alacritty,
    "foot": _read_foot,
    "windows-terminal": _read_windows_terminal,
    "termux": _read_termux,
}


def read_back(fmt, text):
    """{role: '#rrggbb'} as the consumer's parser sees it. Raises on a parse failure."""
    if fmt not in READERS:
        raise ValueError(f"unknown format {fmt!r}")
    return READERS[fmt](text)


def variants():
    """The variant ids this tree DECLARES — scripts/variant_roster.py (W61 B2)."""
    import variant_roster
    return variant_roster.ids()


def formats():
    """The formats the EMITTER declares it emits (make_konsole.TERMINAL_FORMATS)."""
    import make_konsole as K
    return sorted(K.TERMINAL_FORMATS)


def drift():
    """[(format, why)] — emitter roster vs reader roster, in BOTH directions."""
    emitted, read = set(formats()), set(READERS)
    return ([(f, "emitted by make_konsole but this check has no reader for it")
             for f in sorted(emitted - read)] +
            [(f, "this check reads it but make_konsole no longer declares it")
             for f in sorted(read - emitted)])


def emit(fmt, variant):
    import make_konsole as K
    return K.TERMINAL_FORMATS[fmt](variant)


def compare(fmt, variant, text=None):
    """[(role, expected, got)] mismatches for one format/variant; [] when faithful."""
    import make_konsole as K
    exp = _expected(K.ansi_table(variant))
    got = read_back(fmt, text if text is not None else emit(fmt, variant))
    return [(k, exp[k], got.get(k)) for k in exp if got.get(k) != exp[k]]


def population():
    """([(variant, fmt)] measurable, [(variant|'*', fmt, why)] missing).

    ⚑ A MEMBER THAT CANNOT BE MEASURED IS RETURNED WITH A REASON, NEVER DROPPED."""
    missing = [("*", f, why) for f, why in drift()]
    bad_fmts = {f for f, _ in drift()}
    cells = [(v, f) for v in variants() for f in formats() if f not in bad_fmts]
    return cells, missing


def measure():
    """The MEASUREMENT policy/terminals.rego decides (W50): both rosters (the
    declared variants, the formats make_konsole declares), the drift between the
    emitter's formats and this check's readers in both directions, and per
    measurable (variant, format) cell either the parse error or the roles whose
    read-back differs from make_konsole.ansi_table. No verdict here."""
    cells, _missing = population()
    cases = []
    for v, fmt in cells:
        c = {"id": f"{fmt} {v}", "variant": v, "format": fmt, "parse_error": None, "mismatches": None}
        try:
            c["mismatches"] = [{"role": r, "want": e, "got": g} for r, e, g in compare(fmt, v)]
        except Exception as e:                       # noqa: BLE001
            c["parse_error"] = f"{type(e).__name__}: {e}"
        cases.append(c)
    return {"variants": list(variants()), "formats": formats(),
            "drift": [{"format": f, "why": why} for f, why in drift()], "cases": cases}


def main(argv):
    known = {"--map", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_terminals: unknown flag {a!r}", file=sys.stderr)
            return 2
    vs, fs = variants(), formats()
    if "--map" in argv:
        for fmt in fs:
            if fmt not in READERS:
                print(f"{fmt:17} NO READER")
                continue
            got = read_back(fmt, emit(fmt, vs[0]))
            print(f"{fmt:17} {len(got)} roles: {' '.join(sorted(got))}")
        for f, why in drift():
            print(f"DRIFT {f}: {why}")
        return 0
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import opa_gate
    return opa_gate.gate("terminals")


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    for fmt in formats():
        check(f"{fmt} emission is faithful", compare(fmt, "EL-Openglo"), [])
    # ⚑ THE LIVENESS CONJUNCT: complete AND not vacuously complete.
    cells, missing = population()
    check("the declared population is complete on a clean tree",
          (missing, len(cells) == len(variants()) * len(formats())), ([], True))
    check("and it is not vacuously complete", len(cells) > 0, True)
    # ⚑ DRIFT MUST BE SEEN IN BOTH DIRECTIONS (synthetic: a reader removed/added)
    saved = dict(READERS)
    try:
        del READERS["foot"]
        check("an emitted format with no reader is missing",
              [f for _v, f, _w in population()[1]], ["foot"])
        m = measure()
        check("...and the measurement reports the drift, and drops no cell silently",
              ([d["format"] for d in m["drift"]], any(c["format"] == "foot" for c in m["cases"])),
              (["foot"], False))
        READERS.clear()
        READERS.update(saved)
        READERS["kitty"] = _read_foot
        check("a reader for a format not emitted is missing",
              [f for _v, f, _w in population()[1]], ["kitty"])
    finally:
        READERS.clear()
        READERS.update(saved)
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
