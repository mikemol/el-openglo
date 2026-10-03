#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""make_vscode.py — the palette as a VS Code colour theme extension, one theme per variant (W161).

    make_vscode.py            # writes vscode/package.json and vscode/themes/<variant>-color-theme.json
    make_vscode.py --vsix     # also packs dist/el-openglo.vsix (a deterministic zip of that folder)
    make_vscode.py --map      # workbench / token key -> palette role
    make_vscode.py --print    # one theme (EL-Openglo) to stdout

⚑ EVERY COLOUR IS A ROLE, NEVER A NUMBER. The workbench colours read the same roles table
make_firefox.roles solves (parse_scheme's roles plus the SEEN ghost and the hover/active fills,
relations.md §3b), and the syntax colours and the integrated terminal read make_konsole.
ansi_table — the sixteen ANSI colours the terminal emitters already keep pairwise separable
under the CVD gate. No hex is spelled here; scripts/check_token_source refuses an emitter that
reads no authority, and scripts/check_vscode.py holds every emitted colour to its role.

⚑ ONE EXTENSION, SIX THEMES. package.json `contributes.themes` lists every variant (uiTheme
`vs-dark` for Off variants, `vs` for Lit), as the dynamic Firefox extension carries all six.

WEAKNESS, STATED. This is the theme JSON and the package manifest, not VS Code's render, and
`vsce` is not run: the .vsix is a zip with the layout the Marketplace documents, unvalidated by
the Marketplace's own tool. The syntax colours are the ANSI bank, so the contrast floors the
check holds them to are the measured ones (check_vscode.FLOORS), not a claim that every ANSI hue
reads on every ground.
"""
import json
import os
import sys
import zipfile

from emitters import LICENSE_SPDX, atomic_write

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
OUT_DIR = os.path.join(ROOT, "vscode")
VSIX = os.path.join(ROOT, "dist", "el-openglo.vsix")
NAME = "el-openglo"
PUBLISHER = "el-openglo"
VERSION = "1.0.0"
ENGINE = "^1.60.0"

# workbench colour key -> palette role. Roles: make_firefox.roles keys (parse_scheme roles and
# the composites ghost_seen / hover_fill / active_fill), text_faint, and ansi.<name>/ansi.bright<Name>.
KEYS: tuple[tuple[str, str], ...] = (
    ("editor.background", "view_bg"), ("editor.foreground", "phosphor"),
    ("editor.selectionBackground", "sel"), ("editor.selectionForeground", "sel_fg"),
    ("editor.lineHighlightBackground", "panel"),
    ("editorCursor.foreground", "accent"),
    ("editorLineNumber.foreground", "text_faint"), ("editorLineNumber.activeForeground", "phosphor"),
    ("editorWhitespace.foreground", "ghost_seen"), ("editorIndentGuide.background1", "ghost_seen"),
    ("editorWidget.background", "panel"), ("editorWidget.foreground", "phosphor"),
    ("editorWidget.border", "ghost_seen"), ("editorGroup.border", "ghost_seen"),
    ("editorGroupHeader.tabsBackground", "ground"),
    ("tab.activeBackground", "view_bg"), ("tab.activeForeground", "phosphor"),
    ("tab.inactiveBackground", "panel"), ("tab.inactiveForeground", "text_faint"),
    ("tab.border", "ghost_seen"), ("tab.activeBorderTop", "accent"),
    ("activityBar.background", "ground"), ("activityBar.foreground", "phosphor"),
    ("activityBar.inactiveForeground", "text_faint"), ("activityBar.border", "ghost_seen"),
    ("activityBarBadge.background", "sel"), ("activityBarBadge.foreground", "sel_fg"),
    ("sideBar.background", "ground"), ("sideBar.foreground", "phosphor"),
    ("sideBar.border", "ghost_seen"), ("sideBarTitle.foreground", "phosphor"),
    ("list.activeSelectionBackground", "sel"), ("list.activeSelectionForeground", "sel_fg"),
    ("list.inactiveSelectionBackground", "hover_fill"), ("list.inactiveSelectionForeground", "phosphor"),
    ("list.hoverBackground", "hover_fill"), ("list.hoverForeground", "phosphor"),
    ("list.focusOutline", "focus"),
    ("statusBar.background", "panel"), ("statusBar.foreground", "phosphor"),
    ("statusBar.border", "ghost_seen"),
    ("titleBar.activeBackground", "ground"), ("titleBar.activeForeground", "phosphor"),
    ("titleBar.inactiveBackground", "ground"), ("titleBar.inactiveForeground", "text_faint"),
    ("input.background", "view_bg"), ("input.foreground", "phosphor"), ("input.border", "ghost_seen"),
    ("focusBorder", "focus"),
    ("button.background", "sel"), ("button.foreground", "sel_fg"), ("button.hoverBackground", "active_fill"),
    ("dropdown.background", "panel"), ("dropdown.foreground", "phosphor"), ("dropdown.border", "ghost_seen"),
    ("panel.background", "view_bg"), ("panel.border", "ghost_seen"),
    ("panelTitle.activeForeground", "phosphor"), ("panelTitle.inactiveForeground", "text_faint"),
    ("panelTitle.activeBorder", "accent"),
    ("terminal.background", "view_bg"), ("terminal.foreground", "phosphor"),
    ("terminalCursor.foreground", "accent"),
    ("foreground", "phosphor"), ("descriptionForeground", "text_faint"),
    ("errorForeground", "ansi.red"), ("textLink.foreground", "accent"),
    ("textLink.activeForeground", "phosphor"), ("selection.background", "sel"),
    ("scrollbarSlider.background", "ghost_seen"), ("scrollbarSlider.hoverBackground", "hover_fill"),
    ("scrollbarSlider.activeBackground", "active_fill"),
    ("editorError.foreground", "ansi.red"), ("editorWarning.foreground", "ansi.yellow"),
    ("editorInfo.foreground", "ansi.blue"),
)
ANSI = ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white")
# the integrated terminal's sixteen: terminal.ansiRed <- ansi.red, terminal.ansiBrightRed <- ansi.brightRed
KEYS += tuple((f"terminal.ansi{n.capitalize()}", f"ansi.normal{n.capitalize()}") for n in ANSI)
KEYS += tuple((f"terminal.ansiBright{n.capitalize()}", f"ansi.bright{n.capitalize()}") for n in ANSI)

# tokenColors: (name, TextMate scopes, role, fontStyle). Hue is the ANSI role's meaning
# (red=error, green=string, yellow=number/constant, blue=function, magenta=keyword, cyan=type).
TOKENS = (
    ("comment", ("comment", "punctuation.definition.comment"), "text_faint", "italic"),
    ("string", ("string", "string.quoted"), "ansi.green", ""),
    ("number and constant", ("constant.numeric", "constant.language", "constant.character"), "ansi.yellow", ""),
    ("keyword", ("keyword", "storage", "storage.type", "keyword.control"), "ansi.magenta", ""),
    ("function", ("entity.name.function", "support.function", "meta.function-call"), "ansi.blue", ""),
    ("type", ("entity.name.type", "entity.name.class", "support.type", "support.class"), "ansi.cyan", ""),
    ("variable", ("variable", "variable.other", "meta.definition.variable"), "phosphor", ""),
    ("operator and punctuation", ("keyword.operator", "punctuation"), "phosphor", ""),
    ("tag", ("entity.name.tag", "meta.tag"), "ansi.red", ""),
    ("attribute", ("entity.other.attribute-name",), "ansi.yellow", ""),
    ("invalid", ("invalid", "invalid.illegal"), "ansi.red", "underline"),
    ("markup heading", ("markup.heading", "entity.name.section"), "accent", "bold"),
    ("markup link", ("markup.underline.link", "string.other.link"), "accent", "underline"),
)


def _hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*(int(x) for x in rgb))


def _rgb(h):
    import make_konsole as K
    return K._rgb(h)


# the WCAG ratio a syntax colour must reach on the editor ground (1.4.11 non-text 3:1; the
# check holds each token to its own declared floor, scripts/check_vscode.FLOORS)
SYNTAX_FLOOR = 3.0


def _legible(color, ground, text, floor=SYNTAX_FLOOR):
    """`color` itself when it already reads on `ground`; else the least pull toward `text` (the
    variant's own text colour, which reads on its ground) that reaches `floor`.

    ⚑ WHY: the Lit grounds are backlit phosphor, light, and the ANSI normal bank was tinted for a
    terminal on either ground; measured 2026-10-03, string / type / function sat at 1.4-2.6:1 on
    the three Lit grounds. A unit step of 0.05 toward the text colour keeps the hue's identity as
    long as it can (make_konsole._tint, the same pull its own ANSI solve uses). The Off variants
    clear the floor unchanged, so nothing moves there."""
    import cvd_gate as C
    import make_konsole as K
    for step in range(21):
        c = K._tint(color, text, step * 0.05)
        if C.wcag_ratio(c, ground) >= floor:
            return c
    return text


def roles(variant):
    """{role: '#rrggbb'} — make_firefox.roles (parse_scheme + composites), text_faint, and the ANSI bank.

    ⚑ THE ANSI BANK IS make_konsole.ansi_table, and WHICH BANK IS BY POLARITY: an Off variant
    (dark ground) reads the bright bank, a Lit variant (light ground) the normal one, so a hue
    is the lighter step on a void and the deeper step on a backlit ground."""
    import make_firefox as MF
    import make_konsole as K
    r = {k: _hex(v) for k, v in MF.roles(variant).items() if isinstance(v, list)}
    t = K.ansi_table(variant)
    r["text_faint"] = _hex(t["fg_faint"])
    lit = variant.endswith("-Lit")
    ground, text = _rgb(r["view_bg"]), _rgb(r["phosphor"])
    for i, n in enumerate(ANSI):
        r[f"ansi.{n}"] = _hex(_legible((t["normal"] if lit else t["bright"])[i], ground, text))
        r[f"ansi.bright{n.capitalize()}"] = _hex(t["bright"][i])
    # the terminal's own normal bank, whatever the polarity; the syntax uses ansi.<name> above
    for i, n in enumerate(ANSI):
        r[f"ansi.normal{n.capitalize()}"] = _hex(t["normal"][i])
    return r


def theme(variant):
    r = roles(variant)
    colors = {}
    for key, role in KEYS:
        colors[key] = r[role]
    token_colors = []
    for name, scopes, role, style in TOKENS:
        settings = {"foreground": r[role]}
        if style:
            settings["fontStyle"] = style
        token_colors.append({"name": name, "scope": list(scopes), "settings": settings})
    return {"$schema": "vscode://schemas/color-theme",
            "name": f"EL Openglo ({variant})",
            "type": "light" if variant.endswith("-Lit") else "dark",
            "semanticHighlighting": True,
            "colors": colors,
            "tokenColors": token_colors}


def variants():
    """The variant ids make_schemes.GRID declares - the emitted palette authority."""
    import make_schemes
    ids = []
    for value in make_schemes.GRID.values():
        t = value[0] if isinstance(value, (list, tuple)) else value
        if isinstance(t, dict) and "id" in t:
            ids.append(t["id"])
    if not ids:
        raise SystemExit("make_vscode: the grid is empty - nothing to emit")
    return sorted(ids)


def theme_path(variant):
    return f"themes/{variant}-color-theme.json"


def package_json(vs=None):
    vs = variants() if vs is None else vs
    return {"name": NAME, "displayName": "EL Openglo", "publisher": PUBLISHER, "version": VERSION,
            "description": "Electroluminescent watch display: six phosphor colour themes, generated from one solved palette",
            "license": LICENSE_SPDX, "engines": {"vscode": ENGINE}, "categories": ["Themes"],
            "contributes": {"themes": [
                {"label": f"EL Openglo ({v})", "uiTheme": "vs" if v.endswith("-Lit") else "vs-dark",
                 "path": "./" + theme_path(v)} for v in vs]}}


def files(vs=None):
    """{relative path: text} for the extension folder."""
    vs = variants() if vs is None else vs
    out = {"package.json": json.dumps(package_json(vs), indent=2) + "\n"}
    for v in vs:
        out[theme_path(v)] = json.dumps(theme(v), indent=2) + "\n"
    return out


CONTENT_TYPES = ('<?xml version="1.0" encoding="utf-8"?>\n'
                 '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                 '<Default Extension=".json" ContentType="application/json"/>'
                 '<Default Extension=".vsixmanifest" ContentType="text/xml"/>'
                 '<Default Extension=".txt" ContentType="text/plain"/></Types>\n')


def vsixmanifest():
    p = package_json()
    return ('<?xml version="1.0" encoding="utf-8"?>\n'
            '<PackageManifest Version="2.0.0" xmlns="http://schemas.microsoft.com/developer/vsx-schema/2011">'
            f'<Metadata><Identity Language="en-US" Id="{p["name"]}" Version="{p["version"]}" Publisher="{p["publisher"]}"/>'
            f'<DisplayName>{p["displayName"]}</DisplayName><Description xml:space="preserve">{p["description"]}</Description>'
            '<Tags>theme,color-theme</Tags><Categories>Themes</Categories><GalleryFlags>Public</GalleryFlags>'
            f'<Properties><Property Id="Microsoft.VisualStudio.Code.Engine" Value="{ENGINE}"/></Properties>'
            '<License>extension/LICENSE.txt</License></Metadata>'
            '<Installation><InstallationTarget Id="Microsoft.VisualStudio.Code"/></Installation><Dependencies/>'
            '<Assets><Asset Type="Microsoft.VisualStudio.Code.Manifest" Path="extension/package.json" Addressable="true"/>'
            '<Asset Type="Microsoft.VisualStudio.Services.Content.License" Path="extension/LICENSE.txt" Addressable="true"/>'
            '</Assets></PackageManifest>\n')


def vsix_entries(vs=None):
    """{zip path: text} — the layout the Marketplace documents (the .vsix is an OPC zip)."""
    with open(os.path.join(ROOT, "LICENSE"), encoding="utf-8") as fh:
        license_text = fh.read()
    out = {"[Content_Types].xml": CONTENT_TYPES, "extension.vsixmanifest": vsixmanifest(),
           "extension/LICENSE.txt": license_text}
    for rel, text in files(vs).items():
        out["extension/" + rel] = text
    return out


def pack_vsix(path=VSIX, vs=None):
    """Write the .vsix deterministically: sorted entries, a fixed timestamp, so a rebuild is byte-equal."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    import io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in sorted(vsix_entries(vs).items()):
            zi = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, text)
    atomic_write(path, buf.getvalue())
    return path


def render_all(out_dir=OUT_DIR, vs=None):
    written = []
    for rel, text in files(vs).items():
        p = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        atomic_write(p, text)
        written.append(p)
    return written


def main(argv):
    known = {"--vsix", "--map", "--print"}
    for a in argv[1:]:
        if a not in known:
            print(f"make_vscode: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--map" in argv:
        for key, role in KEYS:
            print(f"{key:40} <- {role}")
        for name, scopes, role, _style in TOKENS:
            print(f"token {name:34} <- {role}")
        return 0
    if "--print" in argv:
        sys.stdout.write(json.dumps(theme("EL-Openglo"), indent=2) + "\n")
        return 0
    w = render_all()
    msg = f"make_vscode: wrote {len(w)} file(s) under {os.path.relpath(OUT_DIR, ROOT)}"
    if "--vsix" in argv:
        msg += f"; packed {os.path.relpath(pack_vsix(), ROOT)}"
    print(msg)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
