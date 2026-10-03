#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_vscode.py — the VS Code theme carries the palette, parses as itself and reads on its ground (W161).

    scripts/check_vscode.py            # the verdict, as opa_gate vscode decides it
    scripts/check_vscode.py --json     # the measurement policy/vscode.rego decides
    scripts/check_vscode.py --map      # workbench / token key -> palette role
    scripts/check_vscode.py --selftest # the measurement can see a wrong colour, a low contrast, a stale file

Per declared variant (variant_roster, the palette authority): whether the committed
vscode/themes/<variant>-color-theme.json exists and parses; every workbench colour and token
colour that is not the role make_vscode names (read afresh from make_firefox.roles and
make_konsole.ansi_table); every colour key no role maps; the theme `type` against the variant's
polarity; whether the file equals a fresh emission; and, read FROM THE FILE, the WCAG contrast of
every declared text pair and of every syntax colour on the editor ground (cvd_gate.wcag_ratio,
the metric the other contrast gates use) against FLOORS. Plus the package: package.json contributes
exactly the roster, each theme path existing with the uiTheme the polarity wants, and the .vsix
packed afresh has the documented layout, one entry per theme, equal to the folder.

WEAKNESS: it proves the files, not VS Code's render. WCAG ratio is luminance only: it does not
judge whether two syntax hues are told apart (the ANSI bank's CVD separation is make_konsole's
gate, held on the terminal, not on code), and the floors are measured ones, declared below, not
a claim that the palette meets AA everywhere. `vsce` is not run, so the .vsix is checked against
the layout, not against the Marketplace.
"""
import json
import os
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

# (foreground key, background key, floor): declared text pairs, keys of the theme's `colors`.
FLOORS = (
    ("editor.foreground", "editor.background", 4.5),
    ("editor.selectionForeground", "editor.selectionBackground", 4.5),
    ("tab.activeForeground", "tab.activeBackground", 4.5),
    ("tab.inactiveForeground", "tab.inactiveBackground", 3.0),
    ("sideBar.foreground", "sideBar.background", 4.5),
    ("activityBar.foreground", "activityBar.background", 4.5),
    ("statusBar.foreground", "statusBar.background", 4.5),
    ("list.activeSelectionForeground", "list.activeSelectionBackground", 4.5),
    ("list.hoverForeground", "list.hoverBackground", 4.5),
    ("input.foreground", "input.background", 4.5),
    ("terminal.foreground", "terminal.background", 4.5),
    ("button.foreground", "button.background", 4.5),
    ("editorLineNumber.foreground", "editor.background", 3.0),
)
# a syntax colour on the editor ground, per token name -> floor; unnamed tokens take the default
TOKEN_FLOOR = 3.0
TOKEN_FLOORS = {"variable": 4.5, "operator and punctuation": 4.5, "keyword": 3.0}


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _ratio(a, b):
    import cvd_gate as C
    return round(C.wcag_ratio(_rgb(a), _rgb(b)), 2)


def contrast_facts(doc):
    """[{pair, ratio, floor}] read from the FILE: declared pairs, then each token on the editor ground."""
    colors = doc.get("colors", {}) if isinstance(doc.get("colors"), dict) else {}
    out = []
    for fg, bg, floor in FLOORS:
        if fg in colors and bg in colors:
            out.append({"pair": f"{fg} on {bg}", "ratio": _ratio(colors[fg], colors[bg]), "floor": floor})
        else:
            out.append({"pair": f"{fg} on {bg}", "ratio": None, "floor": floor})
    ground = colors.get("editor.background")
    for t in doc.get("tokenColors", []) if isinstance(doc.get("tokenColors"), list) else []:
        fgc = t.get("settings", {}).get("foreground")
        if fgc and ground:
            out.append({"pair": f"token {t.get('name')} on editor.background",
                        "ratio": _ratio(fgc, ground),
                        "floor": TOKEN_FLOORS.get(t.get("name"), TOKEN_FLOOR)})
    return out


def facts(variant, text):
    """What one theme file SAYS - no verdict (policy/vscode.rego rules). parse_error non-null => the rest is null."""
    import make_vscode as MV
    want_type = "light" if variant.endswith("-Lit") else "dark"
    try:
        doc = json.loads(text)
        if not isinstance(doc, dict):
            raise ValueError("not a JSON object")
    except ValueError as e:
        return {"id": variant, "present": True, "parse_error": str(e), "wrong_colours": None,
                "unmapped_keys": None, "wrong_tokens": None, "type": None, "want_type": want_type,
                "contrast": None, "current": None}
    r = MV.roles(variant)
    colors = doc.get("colors", {}) if isinstance(doc.get("colors"), dict) else {}
    wrong = [{"key": k, "role": role, "got": colors.get(k), "want": r[role]}
             for k, role in MV.KEYS if colors.get(k) != r[role]]
    toks = {t.get("name"): t for t in doc.get("tokenColors", []) if isinstance(t, dict)}
    wrong_tokens = [{"name": name, "role": role, "got": toks.get(name, {}).get("settings", {}).get("foreground"),
                     "want": r[role]}
                    for name, _s, role, _st in MV.TOKENS
                    if toks.get(name, {}).get("settings", {}).get("foreground") != r[role]]
    return {"id": variant, "present": True, "parse_error": None, "wrong_colours": wrong,
            "unmapped_keys": sorted(set(colors) - {k for k, _ in MV.KEYS}),
            "wrong_tokens": wrong_tokens, "type": doc.get("type"), "want_type": want_type,
            "contrast": contrast_facts(doc), "current": text == MV.files([variant])[MV.theme_path(variant)]}


def package_facts(folder, roster):
    """What the committed package.json says against the roster."""
    import make_vscode as MV
    p = os.path.join(folder, "package.json")
    if not os.path.exists(p):
        return {"present": False}
    try:
        pj = json.load(open(p, encoding="utf-8"))
        themes = pj["contributes"]["themes"]
    except (ValueError, KeyError, TypeError) as e:
        return {"present": True, "parse_error": f"{type(e).__name__}: {e}"}
    by_path = {t.get("path"): t for t in themes}
    want = {"./" + MV.theme_path(v): v for v in roster}
    return {"present": True, "parse_error": None,
            "missing": sorted(v for pth, v in want.items() if pth not in by_path),
            "extra": sorted(str(pth) for pth in by_path if pth not in want),
            "missing_files": sorted(v for pth, v in want.items()
                                    if not os.path.exists(os.path.join(folder, pth[2:]))),
            "wrong_ui": sorted(v for pth, v in want.items() if pth in by_path and
                               by_path[pth].get("uiTheme") != ("vs" if v.endswith("-Lit") else "vs-dark")),
            "current": text_of(p) == MV.files(roster)["package.json"],
            "engine": pj.get("engines", {}).get("vscode"), "publisher": pj.get("publisher")}


def text_of(path):
    return open(path, encoding="utf-8").read()


def vsix_facts(roster):
    """What a .vsix packed afresh into private staging says: it opens as a zip, carries the documented
    entries, one per theme, and each equals the folder's emission."""
    import make_vscode as MV
    with tempfile.TemporaryDirectory() as td:
        path = MV.pack_vsix(os.path.join(td, "t.vsix"), roster)
        try:
            with zipfile.ZipFile(path) as z:
                names = sorted(z.namelist())
                bad = z.testzip()
                content = {n: z.read(n).decode("utf-8") for n in names}
        except zipfile.BadZipFile as e:
            return {"opens": False, "why": str(e)}
    want = MV.vsix_entries(roster)
    return {"opens": True, "corrupt_member": bad,
            "missing": sorted(set(want) - set(names)), "extra": sorted(set(names) - set(want)),
            "differs": sorted(n for n in names if n in want and content[n] != want[n]),
            "required": [n for n in ("[Content_Types].xml", "extension.vsixmanifest", "extension/package.json")
                         if n not in names]}


def measure(folder=None):
    import make_vscode as MV
    import variant_roster
    folder = folder or MV.OUT_DIR
    roster = list(variant_roster.ids())
    cases = []
    for v in roster:
        p = os.path.join(folder, MV.theme_path(v))
        if not os.path.exists(p):
            cases.append({"id": v, "present": False})
            continue
        cases.append(facts(v, text_of(p)))
    tdir = os.path.join(folder, "themes")
    orphans = sorted(f for f in os.listdir(tdir)
                     if f not in {os.path.basename(MV.theme_path(v)) for v in roster}) if os.path.isdir(tdir) else []
    return {"roster": roster, "cases": cases, "orphans": orphans,
            "package": package_facts(folder, roster), "vsix": vsix_facts(roster)}


def _selftest():
    import make_vscode as MV
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    v = "EL-Openglo"
    good = MV.files([v])[MV.theme_path(v)]
    f = facts(v, good)
    chk("the real emission measures faithful", (f["parse_error"], f["wrong_colours"], f["unmapped_keys"],
                                              f["wrong_tokens"], f["type"] == f["want_type"], f["current"]),
        (None, [], [], [], True, True))
    d = json.loads(good)
    d["colors"]["editor.background"] = "#ffffff"
    f = facts(v, json.dumps(d))
    chk("a wrong ground is seen, and so is the low contrast it makes",
        ([w["key"] for w in f["wrong_colours"]], f["current"],
         any(c["pair"] == "editor.foreground on editor.background" and c["ratio"] < c["floor"] for c in f["contrast"])),
        (["editor.background"], False, True))
    d = json.loads(good)
    d["colors"]["madeUp.key"] = "#000000"
    d["tokenColors"][1]["settings"]["foreground"] = "#010203"
    f = facts(v, json.dumps(d))
    chk("an unmapped key and a wrong token colour are seen",
        (f["unmapped_keys"], [t["name"] for t in f["wrong_tokens"]]), (["madeUp.key"], ["string"]))
    d = json.loads(good)
    d["type"] = "light"
    chk("a wrong polarity is seen", facts(v, json.dumps(d))["type"], "light")
    chk("unparsable JSON is a parse error and nothing else is claimed",
        (facts(v, "{")["parse_error"] is not None, facts(v, "{")["contrast"]), (True, None))
    with tempfile.TemporaryDirectory() as td:
        MV.render_all(td, [v])
        pf = package_facts(td, [v, "EL-Azure"])
        chk("a package missing a roster variant is seen, with its file", (pf["missing"], pf["missing_files"]),
            (["EL-Azure"], ["EL-Azure"]))
        pj = json.load(open(os.path.join(td, "package.json"), encoding="utf-8"))
        pj["contributes"]["themes"][0]["uiTheme"] = "vs"
        json.dump(pj, open(os.path.join(td, "package.json"), "w", encoding="utf-8"))
        chk("a wrong uiTheme is seen", package_facts(td, [v])["wrong_ui"], [v])
    vf = vsix_facts([v])
    chk("a fresh vsix opens with the documented entries and nothing differs",
        (vf["opens"], vf["required"], vf["missing"], vf["extra"], vf["differs"]), (True, [], [], [], []))
    m = measure()
    chk("every declared variant is measured and none is vacuous", (len(m["cases"]) == len(m["roster"]) > 0), True)
    print("check_vscode selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    for a in argv[1:]:
        if a not in {"--json", "--map", "--selftest"}:
            print(f"check_vscode: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    import make_vscode as MV
    if "--map" in argv:
        for key, role in MV.KEYS:
            print(f"{key:40} <- {role}")
        return 0
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate
    return opa_gate.gate("vscode")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
