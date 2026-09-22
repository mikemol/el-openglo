#!/usr/bin/env python3
"""display_params — the DISPLAY layer of the settings, declared ONCE (W59; catalog/one-display.md).

Three Plasma packages mount one display (SegmentChar / ApertureField): the clock,
the marquee, the live wallpaper. A display parameter governs how a primitive is
DRAWN and means the same on every mount. It is declared here, and each mount's
kcfg and config page INCLUDE it through loader holes ($displayEntries in the kcfg;
$displayDecls and $displayControls on the page). Mount rows (use24h, speed, …) and
instrument rows (debugLog, traceLog) stay hand-written in each template: that
repetition carries identity.

⚑ EVERY MOUNT ANSWERS FOR EVERY PARAMETER: Exposed(spelling, …) or
Withheld(reason). A parameter a mount does not mention is an UNEXPLAINED ABSENCE,
and scripts/check_config_page.py (policy/config_page.rego, D-rules) refuses it.

⚑ LEGACY KEYS ARE KEPT AS SPELLINGS, NOT MIGRATED. A plasmoid's settings live in
plasma-org.kde.plasma.desktop-appletsrc under the applet's own group; a package
ships no kconf_update step, and a QML-side copy (read old key, write new) would
need BOTH keys in the kcfg forever anyway. Renaming `showField` to `showGhost`
would silently reset every user's setting. So the canonical key names the
parameter; `spelling` is the key a mount has always stored it under.

⚑ WHAT one-display.md EQUATED, MEASURED AGAINST THE DISPLAY'S OWN PROPERTIES
(SegmentChar.qml has ghostAlpha AND ghostWeight; ApertureField has dotFill and
ghostOpacity and no per-layer stroke, no bloom): ghostWeight is NOT ghostAlpha
(stroke thickness vs opacity) and weight is NOT dotFill (a lit-only boost vs one
size for lit and unlit). They are separate parameters here, each withheld where
its display cannot draw it. digitGap and pitchScale ARE one parameter (the
lattice pitch) in two mount-local units, recorded per spelling.

WEAKNESS: `Exposed` is a claim about the emitted kcfg and page, which the check
measures; whether the MOUNT'S main.qml reads the key is not measured here.
"""
import string
from dataclasses import dataclass


@dataclass(frozen=True)
class Param:
    key: str        # canonical name
    type: str       # kcfg type: Bool | Double
    label: str      # the ONE label every mount shows
    meaning: str


@dataclass(frozen=True)
class Exposed:
    spelling: str           # the kcfg key this mount stores it under (legacy kept)
    default: str            # kcfg default; `$hole`s filled from the emitter's holes
    control: tuple = ()     # () a CheckBox; (from, to, step) a Slider — may hold $holes
    note: str = ""          # emitted as a kcfg comment (unit, provenance)


@dataclass(frozen=True)
class Withheld:
    reason: str


DISPLAY = (
    Param("ghost", "Bool", "Show unlit substrate:", "is the unlit substrate visible at all"),
    Param("ghostOpacity", "Double", "Unlit opacity:", "the unlit substrate's opacity"),
    Param("litWeight", "Double", "Lit stroke weight:", "the lit primitive's fullness over the unlit (luminance x area)"),
    Param("ghostWeight", "Double", "Unlit stroke weight:", "the unlit primitive's stroke thickness"),
    Param("fill", "Double", "Primitive fill:", "a primitive's size as a fraction of its cell, lit and unlit alike"),
    Param("pitch", "Double", "Cell pitch:", "the lattice pitch between cells"),
    Param("bloom", "Double", "Bloom / glow:", "the emission spread around a lit primitive"),
)

_BAKED_ALPHA = ("the palette SOLVES the ghost alpha and it is baked (global across variants, "
                "check_ghost_surfaces measures it); this mount carries no per-user override")
_SEG_FILL = ("SegmentChar's stroke is the substrate's module stroke (segment_topology.MODULE_METRICS); "
             "litWeight and ghostWeight scale it per layer, so a one-size fill would double-count")
_PIP_ONE_SIZE = ("ApertureField draws lit and unlit pips at ONE size (fill); it has no per-layer "
                 "stroke, so this key would be a control that moves nothing")

MOUNTS = {
    "clock": {
        "ghost": Exposed("showGhost", "true"),
        "ghostOpacity": Withheld(_BAKED_ALPHA + " (looked-at alpha)"),
        "litWeight": Exposed("weight", "1.0", ("0", "1", "0.25")),
        "ghostWeight": Exposed("ghostWeight", "0.4", ("0.3", "1.0", "0.05"),
                               "0.4: the operator's live tuning promoted to the default (2026-09-22)"),
        "fill": Withheld(_SEG_FILL),
        "pitch": Exposed("digitGap", "$digitGap", ("$digitGapMin", "2.0", "0.05"),
                         "in segLen: the gap between digit boxes; 1.5x the datasheet module gap, "
                         "and the slider's floor is the module pitch itself"),
        "bloom": Exposed("bloom", "4.0", ("0", "6", "0.5"),
                         "4.0: the operator's live tuning promoted to the default (2026-09-22)"),
    },
    "marquee": {
        "ghost": Exposed("showField", "true"),
        "ghostOpacity": Exposed("ghostAlpha", "$ghostAlpha", ("0.0", "1.0", "0.02"),
                                "the DEFAULT is the palette's SOLVED ghost alpha, filled at emit "
                                "time; the slider is a per-user override, never the source"),
        "litWeight": Withheld(_PIP_ONE_SIZE),
        "ghostWeight": Withheld(_PIP_ONE_SIZE),
        "fill": Exposed("dotFill", "0.82", ("0.5", "1.0", "0.02"),
                        "dot diameter as a fraction of the pitch"),
        "pitch": Exposed("pitchScale", "1.0", ("0.5", "1.5", "0.05"),
                         "a fraction of the panel-derived pitch"),
        "bloom": Withheld("ApertureField has no emission model (no halo layer; the software scene "
                          "graph the gates run has no MultiEffect) — a bloom key would be a slider "
                          "that moves nothing, the defect the clock once shipped twice"),
    },
    "wallpaper": {
        "ghost": Exposed("showGhost", "true"),
        "ghostOpacity": Withheld(_BAKED_ALPHA + " (glanced-at alpha)"),
        "litWeight": Exposed("weight", "1.0", ("0", "1", "0.25")),
        "ghostWeight": Exposed("ghostWeight", "0.81", ("0.3", "1.0", "0.05")),
        "fill": Withheld(_SEG_FILL),
        "pitch": Withheld("the face is FIT to the frame at the substrate's module pitch (60% of the "
                          "width over four cells); a user gap would be a second fit rule, not yet designed"),
        "bloom": Exposed("bloom", "1.5", ("0", "6", "0.5")),
    },
}

_QTYPE = {"Bool": "bool", "Double": "real"}


def param(key):
    return next(p for p in DISPLAY if p.key == key)


def exposed(mount, mounts=None):
    """[(Param, Exposed)] in DISPLAY order."""
    m = (mounts or MOUNTS)[mount]
    return [(p, m[p.key]) for p in DISPLAY if isinstance(m.get(p.key), Exposed)]


def _fill(text, holes):
    return string.Template(text).substitute(**holes) if "$" in text else text


def kcfg_entries(mount, holes=None, indent=" "):
    """The mount's display `<entry>` lines — the $displayEntries hole."""
    holes = holes or {}
    out = [f"{indent}<!-- DISPLAY layer: display_params.MOUNTS[{mount!r}] (do not hand-edit here) -->"]
    for p, e in exposed(mount):
        if e.note:
            out.append(f"{indent}<!-- {p.key}: {e.note} -->")
        out.append(f'{indent}<entry name="{e.spelling}" type="{p.type}">'
                   f"<default>{_fill(e.default, holes)}</default></entry>")
    return "\n".join(out)


def qml_decls(mount, indent="    "):
    """alias + Default declarations — the $displayDecls hole."""
    out = [f"{indent}// DISPLAY layer: display_params.MOUNTS[{mount!r}]"]
    for p, e in exposed(mount):
        prop = "checked" if p.type == "Bool" else "value"
        out.append(f"{indent}property alias cfg_{e.spelling}: {e.spelling}Control.{prop}")
    for p, e in exposed(mount):
        out.append(f"{indent}property {_QTYPE[p.type]} cfg_{e.spelling}Default")
    return "\n".join(out)


def qml_controls(mount, holes=None, indent="        "):
    """One control per exposed parameter, under the canonical label — $displayControls."""
    holes = holes or {}
    out = []
    for p, e in exposed(mount):
        if p.type == "Bool":
            out.append(f'{indent}QQC2.CheckBox {{ id: {e.spelling}Control; '
                       f'Kirigami.FormData.label: "{p.label}" }}')
        else:
            lo, hi, st = (_fill(x, holes) for x in e.control)
            out.append(f"{indent}QQC2.Slider {{ id: {e.spelling}Control; from: {lo}; to: {hi}; "
                       f'stepSize: {st}; Kirigami.FormData.label: "{p.label}" }}')
    return "\n".join(out)


def holes_for(mount, holes=None):
    """The three include holes for a mount, ready to pass to templates.loader.render."""
    return {"displayEntries": kcfg_entries(mount, holes),
            "displayDecls": qml_decls(mount),
            "displayControls": qml_controls(mount, holes)}
