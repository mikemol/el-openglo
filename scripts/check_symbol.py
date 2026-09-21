#!/usr/bin/env python3
"""check_symbol.py — the per-symbol witness for the design log's open work.

⚑ WHY THIS EXISTS.  The design log's 35 open items lived as PROSE that a reader
summarised. `cotype_index.py` made the log queryable — sessions, symbols, ledger
buckets — but every claim in `catalog/cotype/` was about the READING APPARATUS
("does the log parse", "is it coherent"), not about the work. Four meta-claims
over thirty-five items. That is a migration stopped halfway: the log became
legible without becoming checkable, so "what is actually done?" still resolved to
someone's reading rather than to the tree.

This tool closes that. Each open symbol gets a WITNESS — a predicate over the
tree that is true when the work exists — so the log's worklist becomes the same
kind of object as the repo's own: open exactly when its check exits non-zero.

    scripts/check_symbol.py <SYMBOL>     # exit 0 iff that symbol's work is present
    scripts/check_symbol.py --list       # every symbol with a witness, and what it is
    scripts/check_symbol.py --status     # all of them, done/open
    scripts/check_symbol.py --unwitnessed  # open symbols with NO witness here
    scripts/check_symbol.py --regressions  # CLOSED symbols whose work left the tree

⚑ AN OPERATOR-BLOCKED SYMBOL GETS NO WITNESS, AND THAT IS NOT AN OMISSION.  The
log's LIVE bucket is work only a human at a real desktop can verify — "does the
boot splash look right", "is the ghost legible at a glance". No predicate over
this tree can discharge one, and writing a green-by-default check for it would
manufacture exactly the unfalsifiable claim the whole worklist refuses. They are
covered by @OPERATOR (are they legible and correctly bucketed), never by @done.

⚑ A WITNESS IS NECESSARY, NOT SUFFICIENT.  `SegmentChar wired into make_clock`
does not prove the clock renders correctly — that is the LIVE half. The witness
asserts the ARTIFACT EXISTS; the operator asserts it is right. Claiming more
would be the same overclaim the log's own `✓PoC` was careful to avoid.

⚑ FIVE OF THE FIRST SEVEN PASSES WERE FALSE, AND THEY FAILED THE SAME WAY: the
witness was aimed at a NOUN THE LOG MENTIONS instead of the CRITERIA THE LOG
STATES.  ⊕PLA2 matched the frame() helper that built the panel it was deferred
FROM; ⊕KVT2 matched the three widgets that shipped, when it means coverage beyond
them; ⊕SEG-FONT-PROJECT matched the PoC the log calls "NOT wired, NOT calibrated,
NOT validated"; ⊕SEG-TABLE-VALIDATE matched the words "cross-check" in a
docstring; ⊕PANEL-LAYOUT matched the basic layout.js it exists to improve on.

A deferred item is usually deferred FROM something adjacent that already exists,
so the near miss is the DEFAULT failure, not an unlucky one. When the log
enumerates what remains ("NOT wired to fontTools, NOT calibrated, NOT validated
against all 44"), that list IS the witness. When it does not, aim at a definition
rather than a mention — a `def`-anchored pattern over the bare word "validate".
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "scripts", "cotype_index.py")


# Symbols no predicate over THIS tree can decide, each with the reason. These are
# not gaps: a witness here would be an unfalsifiable claim wearing a checkmark.
UNWITNESSABLE = {
    "⊕GTK-ADW": "the log calls it unreachable by design — pure-libadwaita apps "
                "honour no override, so no artifact here can satisfy it (:704)",
}


def _reads(path, pat, count=1):
    """True iff `path` matches `pat` at least `count` times."""
    p = os.path.join(ROOT, path)
    if not os.path.isfile(p):
        return False
    text = open(p, encoding="utf-8", errors="replace").read()
    return len(re.findall(pat, text)) >= count


def _any(paths, pat):
    return any(_reads(p, pat) for p in paths)


# symbol -> (what the witness looks for, predicate)
# ⚑ EACH PREDICATE IS DERIVED FROM THE LOG'S OWN STATEMENT of the item, cited by
# line. A witness invented from the symbol's NAME would test my paraphrase.
def _emitted_clock_is_vector():
    """The EMITTED clock QML has no Canvas and draws segments as antialiased items.

    Reads the artifact the way check_template_parity does — through the
    generator's accessor with a real token dict — so a template edit is what is
    measured, not the generator's source text."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    os.chdir(ROOT)                       # make_clock reads sibling files by bare name
    import make_clock
    import make_schemes
    t = next(v[0] for v in make_schemes.GRID.values())
    qml = make_clock.main_qml(t)
    no_canvas = re.search(r"\bCanvas\b|ctx\.fill|getContext", qml) is None
    segment = re.search(r"component Segment:.*?(Rectangle|Shape)\s*\{.*?antialiasing:\s*true",
                        qml, re.S) is not None
    return no_canvas and segment


def _tool(*args):
    """True iff a repo tool exits 0 — the witness IS the tool that owns the question."""
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", args[0]), *args[1:]],
                       cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0


WITNESS = {
    # ── BUILD: touches the shipped package ──
    # ⚑ THIS WAS A NOUN WITNESS — `SegmentChar` mentioned in four surfaces — the
    # exact near-miss the docstring above warns of, and it read as DONE while the
    # log's fourth gate had never been run. The log states four gates (:4427-4432);
    # check_geometry_source owns reachable + observable (default mode) and
    # coverable (--coverable, 3 arms: a lattice edit reaches every surface, an
    # absent glyph is refused). Session 67 records the closure with those tools.
    "⊕SEGMENT-SUBSTRATE": (
        "one geometry substrate under wallpaper/clock/marquee/plymouth: every surface"
        " reads it, none owns a table, a lattice edit reaches all, an absent glyph"
        " is refused; the four gates are stated at :4427 (:4399)",
        lambda: _tool("check_geometry_source.py") and
                _tool("check_geometry_source.py", "--coverable")),
    # ⚑ REOPENED FROM ⊕SEGMENT-SUBSTRATE'S CLOSURE (session 69). The substrate is
    # the geometry SOURCE on every surface — that closed. Whether any surface USES
    # the substrate's COMPONENT, and draws the palette's ghost, is this: the
    # witness is the tool that asks what each surface EMITS.
    "⊕SEGMENT-ROLLOUT": (
        "every surface draws the palette's fg/fg_in at ghost_alpha rather than deriving"
        " its own on the way in; check_ghost_surfaces measures what each emits (:4419)",
        lambda: _tool("check_ghost_surfaces.py")),
    "⊕NOTIFY-MATRIXRENDER": (
        "the marquee renders via a MATRIX, not a font — the topology the user corrected (:4524)",
        lambda: _reads("make_notify_marquee.py", r"(?i)matrix")),
    "⊕MATRIX-FONT-INPUT": (
        "arbitrary text reaches the matrix by rasterising a font into it (:4534)",
        lambda: _reads("make_notify_marquee.py", r"(?i)rasteri|font.*matrix|matrix.*font")),

    # ── RESEARCH: design work, no package impact ──
    # ⚑ THE LOG STATES THIS ONE'S CRITERIA AND MY FIRST WITNESS IGNORED THEM.  It
    # matched the PoC and reported done, while the log says outright: "PoC-level
    # … NOT wired to fontTools glyph ingest, NOT calibrated, NOT validated against
    # all 44. A proven PRINCIPLE, not a shipped pipeline" (:4644). When the log
    # enumerates what remains, the witness is that list — not the name.
    "⊕SEG-FONT-PROJECT": (
        "wired to real fontTools glyph ingest and validated across all 44 glyphs,"
        " not the synthetic-stroke PoC (:4644)",
        lambda: _reads("project_font.py", r"(?i)fontTools|TTFont") and
                _reads("project_font.py", r"(?i)all.?44|validate")),
    "⊕SEG-PROJECT-CALIBRATE": (
        "bandwidth/tau CALIBRATED from agreement with the authored 44, not hand-set (:4631)",
        lambda: _any(["project_font.py", "glyph_match.py"],
                     r"(?i)calibrat|bandwidth.*agree|tau.*agree")),
    # ⚑ MATCHED THE WORD IN A COMMENT.  The first witness hit "cross-check" inside
    # a segment_topology docstring — prose ABOUT the idea, not a routine doing it.
    # A witness over source must aim at a definition, not a noun.
    "⊕SEG-TABLE-VALIDATE": (
        "a routine that cross-checks the projection against the authored table,"
        " not a comment mentioning the idea (:4632)",
        lambda: _any(["project_font.py", "glyph_match.py", "segment_topology.py"],
                     r"def\s+\w*(?:validate|crosscheck|cross_check)\w*")),
    "⊕SEG22-DESCENDERS": (
        "lowercase g/j/p/q/y carry descender segments in a 22-seg glyph table (:4455)",
        lambda: _reads("segment_topology.py", r"LETTERS22|DESCENDER_GLYPHS|glyph22")),
    "⊕GHOST-DENSITY": (
        "ghost separation re-verified at 22-seg inter-stroke density, where strokes"
        " tighten and the same Lc may read mushier (:4459)",
        lambda: _any(["scripts/check_selection_contrast.py", "cvd_gate.py",
                      "glance_audit.py"], r"(?i)inter.?stroke|density.*ghost|ghost.*density")),

    # ── TUNE ──
    "⊕SOLVER-PERF": (
        "the solver memoizes across variants rather than re-solving each (:4182)",
        lambda: _reads("make_schemes.py", r"_palette-cache|_solved_grid") or
                _reads("make_palette.py", r"(?i)memo|lru_cache")),
    "⊕SOLVER-UI-TOKENS": (
        "the ~5 UI tokens are solved rather than authored (:3928)",
        lambda: _reads("make_palette.py", r"(?i)ui_token|solve_ui")),
    "⊕ICONS-INHERIT": (
        "an icon theme that INHERITS rather than reimplements a set (:2774)",
        lambda: _any(["make_deb.py", "make_plasma.py"], r"(?i)Inherits=.*icon|icon.*Inherits")),
    "⊕CURSOR-INHERIT": (
        "a cursor theme that inherits (:2806)",
        lambda: _any(["make_deb.py", "make_plasma.py"], r"(?i)cursor.*Inherits|Inherits=.*cursor")),
    # The BASIC layout.js already ships (it sets wallpaper + adds the clock); the
    # item is a RICHER template than that (:2785). Witnessing layout.js at all
    # reports the thing being improved on as the improvement.
    "⊕PANEL-LAYOUT": (
        "a richer layout template than the basic wallpaper+clock one that ships —"
        " panel arrangement, systray, task manager (:2785)",
        lambda: _reads("make_deb.py", r"(?i)systemtray|taskmanager|panel\.addWidget")),
    "⊕TASKSWITCH": (
        "an Alt+Tab task switcher in the Plasma Style (:2787)",
        lambda: _any(["make_plasma.py", "make_deb.py"], r"(?i)windowswitcher|tabbox|taskswitch")),

    # ── TIER 3 ──
    # ⚑ THE WITNESS LOOKED IN THE GENERATOR FOR ONE IDIOM.  It read make_clock.py
    # for `Shape {` / `ShapePath` / `SegmentChar` — but the QML was extracted to
    # templates/clock-main.qml (@TEMPLATES), and the log's criterion (:4221-4225)
    # is "no Canvas fill for digits; strokes as scene-graph vector, GPU-AA on".
    # The emitted clock draws every segment as an antialiased scene-graph
    # Rectangle and has no Canvas at all — vector by the log's own definition,
    # in an idiom the regex did not know. Measured 2026-09-20: the witness was
    # stale on both FILE and IDIOM, and read OPEN for a surface that was done.
    # It now reads the EMITTED artifact and asks the criterion.
    "⊕CLOCK-VECTOR": (
        "the clock draws vector segments rather than raster — no Canvas in the emitted"
        " QML, every segment a scene-graph item with antialiasing (:4228)",
        lambda: _emitted_clock_is_vector()),
    # ⚑ PLYMOUTH IS PNG-BAKED BY DESIGN and the log says what vector means there:
    # "pre-render at target res or SVG support if the theme allows" (:4229). The
    # splash renders PIL polygons from the substrate at a FIXED U=48, so it is
    # neither. The witness asks for either form, not for the word.
    "⊕PLYMOUTH-VECTOR": (
        "the boot splash is vector rather than PNG-baked: rendered at the target"
        " resolution, or emitted as SVG (:4228)",
        lambda: _reads("make_plymouth.py", r"(?i)target.?res|screen.?(w|width|res)|\.svg\b")),

    # ── RESIDUE: kept, deliberately unbuilt ──
    # ⚑ THE COMPONENT WITH NO CONSUMER (session 69-70). The colour relation now
    # holds on every surface in its own idiom; this asks whether any shipped
    # surface INSTANTIATES the shared component — an idiom question, kept open.
    "⊕SEGMENTCHAR-ADOPT": (
        "a shipped surface instantiates templates/SegmentChar.qml rather than drawing"
        " segments in its own idiom (:4419)",
        lambda: _any(["templates/live-wallpaper-main.qml", "templates/clock-main.qml",
                      "templates/marquee-main.qml"], r"\bSegmentChar\s*\{")),
    "⊕NOTIFY-SEGRENDER": (
        "the ticker renders in the actual 7-seg/dot primitive (:3568)",
        lambda: _reads("make_notify_marquee.py", r"(?i)SegmentChar|segment_topology")),
    "⊕SUPERSAMPLE-WP": (
        "the wallpaper generator supersamples at generation time (:2583)",
        lambda: _reads("make_wallpaper.py", r"(?i)supersampl|scale\s*=\s*[2-9]")),
    "⊕HDR-EMIT": (
        "extended-range colour is emitted, once Qt exposes it to QML (:2411)",
        lambda: _any(["make_schemes.py", "make_clock.py"], r"(?i)\bhdr\b|extended.?range")),
    "⊕VER-SYSCLOCK": (
        "the system clock itself renders in EL, not only the plasmoid (:2074)",
        lambda: _reads("make_deb.py", r"(?i)sysclock|system.*clock")),
    # ⚑ ⊕GTK-ADW HAS NO WITNESS AND MUST NOT GET ONE.  The log calls it
    # "unreachable by design" (:704): pure-libadwaita apps honour no override, so
    # NO artifact in this tree can ever satisfy it. My first witness matched
    # `gtk-4.0` in make_deb and reported it DONE — dressing an impossibility as an
    # achievement. It belongs in UNWITNESSABLE below, beside the operator-blocked
    # work, for the same reason: no predicate here decides it.
    # Buttons, line edits and the segmented progress bar SHIPPED; ⊕KVT2 is the
    # FULL vocabulary beyond them, deferred "if the element vocabulary proves
    # large" (:585). Witnessing the shipped three would report the deferral done.
    "⊕KVT2": (
        "Kvantum coverage beyond the shipped buttons/line-edits/progress-bar —"
        " scrollbars, sliders, tabs, menus (:585)",
        lambda: _reads("make_kvantum.py", r"(?i)ScrollBar|Slider|TabWidget|MenuItem")),
    # ⚑ THIS WITNESS WAS WRONG ONCE, AND IT PASSED.  It matched `FrameSvg|prefix`,
    # which hits the generic frame() helper building the panel/dialog/tooltip that
    # were DONE. What ⊕PLA2 defers is the WIDGET-BY-WIDGET SVGs — tasks, buttons,
    # sliders — whose "prefix vocabularies are larger and each wrong ID renders
    # invisible chrome" (:541). A witness aimed at the wrong noun reports the
    # completed work as evidence for the deferred work.
    "⊕PLA2": (
        "widget-by-widget Plasma SVGs (tasks/buttons/sliders), not just the panel,"
        " dialog and tooltip frames that shipped (:541)",
        lambda: _reads("make_plasma.py", r"(?i)\btasks\b|\bbutton\b|\bslider\b")),
    "⊕KNB2": (
        "the designer's export is wired through the actual generators (:787)",
        lambda: _any(["make_palette.py", "make_schemes.py"], r"(?i)designer|phosphor-designer")),
}


def _emitted_surfaces():
    """{name: emitted QML} for every shipping segment surface, through the
    generators' accessors with a real token dict — the artifact, not the source."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    os.chdir(ROOT)
    import make_clock
    import make_schemes
    import make_wallpaper_live
    t = next(v[0] for v in make_schemes.GRID.values())
    return {"clock": make_clock.main_qml(t),
            "live-wallpaper": make_wallpaper_live.main_qml("EL-Openglo")}


def _arith(expr, **env):
    """Evaluate an arithmetic expression (+ - * / parentheses, names in env)."""
    import ast
    node = ast.parse(expr.strip(), mode="eval").body
    ops = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b,
           ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b}

    def ev(n):
        if isinstance(n, ast.Constant):
            return float(n.value)
        if isinstance(n, ast.Name):
            return float(env[n.id])
        if isinstance(n, ast.Attribute):          # root.weight -> weight
            return float(env[n.attr])
        if isinstance(n, ast.BinOp):
            return ops[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp) and isinstance(n.op, ast.USub):
            return -ev(n.operand)
        raise ValueError(f"not arithmetic: {ast.dump(n)}")
    return ev(node)


def _stroke_ratio(qml):
    """lit/ghost stroke-thickness ratio at weight=1 from the emitted properties
    `strokeLit:` and `strokeGhost:`, or None when a surface does not declare them."""
    m_lit = re.search(r"property real strokeLit:\s*([^\n]+)", qml)
    m_gh = re.search(r"property real strokeGhost:\s*([^\n]+)", qml)
    if not (m_lit and m_gh):
        return None
    env = {"weight": 1.0, "ghostWeight": 0.81, "segThick": 1.0}
    try:
        return _arith(m_lit.group(1), **env) / _arith(m_gh.group(1), **env)
    except (ValueError, KeyError, ZeroDivisionError):
        return None


def _bloom_is_blur(qml):
    """A MultiEffect blur layer gated by the `bloom` config, on a lit-only layer:
    the ghost colour must not be drawn inside the layered item."""
    if not re.search(r"MultiEffect\s*\{[^}]*blurEnabled:\s*true", qml):
        return False
    if not re.search(r"layer\.enabled:\s*root\.bloom\s*>\s*0", qml):
        return False
    # the ITEM that owns `layer.enabled` (brace-matched) must not draw the ghost
    for m in re.finditer(r"layer\.enabled:", qml):
        depth, start = 0, None
        for i in range(m.start(), -1, -1):          # back to the item's own `{`
            if qml[i] == "}":
                depth += 1
            elif qml[i] == "{":
                if depth == 0:
                    start = i
                    break
                depth -= 1
        depth, end = 0, None
        for i in range(start, len(qml)):            # forward to its `}`
            if qml[i] == "{":
                depth += 1
            elif qml[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if start is None or end is None or "ghostColor" in qml[start:end]:
            return False
    return True


def _closed_stroke_weight():
    surfaces = _emitted_surfaces()
    ratios = {n: _stroke_ratio(q) for n, q in surfaces.items()}
    return all(r is not None and r > 1.0 for r in ratios.values())


def _closed_bloom():
    return all(_bloom_is_blur(q) for q in _emitted_surfaces().values())


# ⚑ CLOSED SYMBOLS HAVE WITNESSES TOO.  Every entry above is for the OPEN set,
# because `--bucket` filters on what the index calls open. A CLOSED symbol's
# "done" was therefore the log's ledger — a hand-written status, the exact
# field CLAUDE.md forbids. Measured 2026-09-21: ⊕BLOOM and ⊕STROKE-WEIGHT closed
# in sessions 40-41 (deb 1.10/1.11), their builds vanished in the recovery, and
# nothing went red — the operator saw it on screen ("the ghost is too close to
# the lit segment"). These predicates re-derive a closure from the emitted
# artifacts; `--regressions` is red when a closed symbol's work is gone.
CLOSED = {
    "⊕STROKE-WEIGHT": (
        "every segment surface draws the lit stroke thicker than the ghost stroke"
        " (T_lit/T_ghost > 1 at weight=1, read from the emitted QML) (:2646)",
        _closed_stroke_weight),
    "⊕BLOOM": (
        "every segment surface blooms by BLURRING a lit-only layer (MultiEffect,"
        " gated by config bloom), never the ghost (:2567)",
        _closed_bloom),
    # ⚑ THE THIRD CLOSED SYMBOL WITH NO BUILD (found 2026-09-21, W17): make_gtk,
    # gtk/, and its gate were all absent; el-openglo-apply skipped the copy behind
    # an isdir guard. The witness is the gate that carries session 14's name set.
    "⊕GTK": (
        "gtk/<id>/gtk{3,4}.css emit, every name a documented libadwaita one, values"
        " the palette's, bg/fg pairs gated (:683)",
        lambda: os.path.isfile(os.path.join(ROOT, "make_gtk.py")) and _tool("check_gtk.py")),
    # ── the sweep of 2026-09-21 (W-sweep): every other closed symbol that names an
    # artifact, witnessed by the tool or definition that IS the artifact ──
    "⊕KONSOLE": ("the Konsole scheme + profile emit and read back through the one ansi table (:2846)",
                 lambda: _tool("check_terminals.py")),
    "⊕CHROME-THEME": ("a valid Chrome manifest per variant from the scheme tokens (:2706)",
                      lambda: _tool("check_chrome.py")),
    "⊕PLYMOUTH": ("the boot splash renders the substrate's digits per variant (:3331)",
                  lambda: _tool("check_plymouth_digits.py")),
    "⊕WALLPAPER-VECTOR": ("the wallpaper is an SVG from the substrate, not a raster (:4233)",
                          lambda: _reads("make_wallpaper.py", r"def\s+wallpaper_svg\b")),
    "⊕WALLPAPER-LIVE": ("a Plasma/Wallpaper package per variant from the live template (:3440)",
                        lambda: _reads("make_wallpaper_live.py", r"def\s+main_qml\b") and
                        os.path.isfile(os.path.join(ROOT, "templates", "live-wallpaper-main.qml"))),
    "⊕NOTIFY-MARQUEE": ("a matrix-rendered notification ticker plasmoid per variant (:3542)",
                        lambda: _reads("make_notify_marquee.py", r"def\s+main_qml\b") and
                        os.path.isfile(os.path.join(ROOT, "templates", "MatrixChar.qml"))),
    "⊕SPLASH": ("the LnF splash reads progress and the palette's ghost (:2910)",
                lambda: _reads("make_deb.py", r"def\s+_splash_qml\b") and
                os.path.isfile(os.path.join(ROOT, "templates", "splash.qml"))),
    "⊕SDDM": ("the SDDM background path ships as el-openglo-sddm (:3074)",
              lambda: _reads("make_deb.py", r"el-openglo-sddm")),
    "⊕LOCKSCREEN": ("the lock screen mounts the live wallpaper (:3001)",
                    lambda: _reads("make_wallpaper_live.py", r"(?i)lock")),
    "⊕KVT": ("the Kvantum recolour: a KvFlat mapper plus the elprogress family (KvFlat itself is EXTERNAL) (:612)",
             lambda: _reads("make_kvantum.py", r"def\s+make_mapper\b") and
             _reads("make_kvantum.py", r"elprogress")),
    "⊕GLANCE-AUDIT": ("the glance audit runs each variant against its parsing-mode floor (:3652)",
                      lambda: _reads("glance_audit.py", r"def\s+run\b")),
    "⊕CONTRAST-STRETCH": ("the lit stretch survives as cvd_gate.stretch_lit (:2487)",
                          lambda: _reads("cvd_gate.py", r"def\s+stretch_lit\b")),
    "⊕APCA-CROSSCHECK": ("APCA is implemented and cross-checked (:3743)",
                         lambda: _reads("cvd_gate.py", r"def\s+apca_Lc\b")),
    "⊕PARAMETRIC-PALETTE": ("the solver derives the scheme from the relations (:3894)",
                            lambda: _reads("make_palette.py", r"def\s+solve_scheme\b")),
    "⊕SEG22": ("the 22-seg geometry is the 16-seg lattice plus six additions (:1576)",
               lambda: _reads("segment_topology.py", r"def\s+geom22\b")),
    "⊕DOT": ("the dot-matrix display component exists (:1002)",
             lambda: os.path.isfile(os.path.join(ROOT, "templates", "MatrixChar.qml"))),
    "⊕VER-PREVIEW": ("the Global Theme previews render from the scheme (:1918)",
                     lambda: _reads("make_preview.py", r"def\s+preview_svg\b") and
                     _reads("make_deb.py", r"contents/previews")),
    # rebuilt W24 (2026-09-21), moved here from LOST: the fonts are peer emitters
    # of the substrate, and check_font holds them to it
    "⊕SEG-FONT": ("an SVG font whose glyphs are the union of the substrate's lit segments (:1252)",
                  lambda: _reads("make_font.py", r"def\s+emit_svg_font\b") and _tool("check_font.py")),
    "⊕SEG-FONT-TTF": ("TTFs built natively from glyph_contours via fontTools, orientation gated on glyf (:1366)",
                      lambda: _reads("make_font.py", r"def\s+build_ttf\b") and
                      _reads("make_font.py", r"def\s+gate_ttf_orientation\b")),
    "⊕DOT-FONT": ("the matrix glyph table drives a font: matrix_contours over MatrixDisplay.glyph (:1068)",
                  lambda: _reads("make_font.py", r"def\s+matrix_contours\b")),
    "⊕DOT-FONT-TTF": ("one build_ttf over a contour source; build_matrix_ttf is a thin wrapper (:1425)",
                      lambda: _reads("make_font.py", r"def\s+build_matrix_ttf\b") and
                      _reads("make_deb.py", r"EL-Matrix|_mf\.OUTPUTS")),
    # rebuilt W26 (2026-09-21): the 5x8 table re-authored, baseline as a LINE
    "⊕DOT-FONT-DESC": ("FONT5x8 with lowercase whose g j p q y descend below a declared baseline line,"
                       " built into a TTF with negative descent (:1496)",
                       lambda: _reads("display_types.py", r"\bFONT5x8_BASELINE\b") and
                       _reads("make_font.py", r"baseline=") and _tool("check_font.py")),
    # rebuilt W25 (2026-09-21), moved here from LOST
    "⊕VER-WIDGET-ICON": ("the plasmoid icon is a lit '12' over its ghost from the substrate (:2058)",
                         lambda: _reads("make_preview.py", r"def\s+icon_svg\b") and
                         _reads("make_deb.py", r"icon_svg\(")),
    "⊕QML-SANITY": ("every staged .qml goes through Qt's qmllint, gated on error ids (:4318)",
                    lambda: _reads("qml_sanity.py", r"def\s+check_qml\b") and
                    _reads("make_deb.py", r"import qml_sanity")),
    "⊕RENDER-GATE": ("make_deb renders the clock and live wallpaper headless and requires lit pixels (:4545)",
                     lambda: _reads("make_deb.py", r"render_nonempty\(") and
                     _reads("qml_sanity.py", r"def\s+render_nonempty\b")),
    "⊕VER-CLOCK-TIME": ("the clock advances by a Timer (:2184)",
                        lambda: os.path.isfile(os.path.join(ROOT, "templates", "clock-main.qml")) and
                        _reads("templates/clock-main.qml", r"Timer\s*\{")),
}

# Closed symbols that name NO artifact this tree could carry: palette decisions
# already witnessed by the worklist's own claims, live observations, naming
# rulings, and symbols subsumed by a later one. Listed so the sweep's coverage
# arm is a choice per symbol rather than an omission.
NO_ARTIFACT = frozenset({
    "⊕AZR", "⊕AMB", "⊕LIT", "⊕GEN", "⊕ITO", "⊕BRT", "⊕KNB", "⊕GIT",   # palette/process decisions, @GRAPH/@SEPARATION witness them
    "⊕AUR", "⊕PLA",                                                   # aurorae/plasma: @EMITTERS + @EBUILD stage them
    "⊕SEG", "⊕SEG16", "⊕SEG16-WIRE", "⊕SEG16-DISTINCT", "⊕SEG-FONT-SPEC-FLIP",  # substrate: @ST22 / segment_topology selftest
    "⊕DOT-WIRE",                                                      # subsumed by ⊕NOTIFY-MARQUEE
    "⊕VER-LNF", "⊕VER-DESKTOP", "⊕VER-THUMB", "⊕VER-DEB", "⊕VER-SURFACE",  # observations at the desktop; @EBUILD stages the LnF
    "⊕GHOST-CONTRAST", "⊕GHOST-CONTRAST-2", "⊕GHOST-CEILING", "⊕HDR-BLACK",  # ghost relations: @GHOST/@GHOSTCOMP
    "⊕SUPERSAMPLE",                                                   # the clock is scene-graph now (⊕CLOCK-VECTOR); FBO moot
    "⊕WALLPAPER-CONTRAST",                                            # subsumed by ⊕GLANCE-AUDIT
    "⊕SOLVER-BACKLIT-CVD", "⊕SOLVER-DEFAULT", "⊕SOLVER-SEMANTIC",     # solver: @PALETTE-CHAIN
    "⊕SEGMENT-SUBSTRATE", "⊕SEGMENT-ROLLOUT", "⊕CLOCK-VECTOR",        # witnessed in WITNESS (open-set table) / @GEOMETRY
})

# ⚑ CLOSED SYMBOLS WHOSE BUILD IS KNOWN LOST.  Found by the sweep of 2026-09-21:
# the design log closes these, the tree does not carry them, and RECOVERY-NOTES
# records the partial. They are neither passed nor silently red: `--regressions`
# prints them as KNOWN-LOST with the waypoint that rebuilds them, and the
# selftest asserts each is STILL absent — a rebuilt one must move to CLOSED, or
# this table has become a stale status of its own.
# ⚑ EMPTY SINCE W26 (2026-09-21): every closed symbol that names an artifact
# now has one. The mechanism stays — the selftest refuses a closure placed
# nowhere, and a LOST entry whose build returns — because the next recovery,
# or the next quiet deletion, will need it. The eight entries this held on
# 2026-09-21 are in git history (075d096).
LOST = {}


def open_symbols():
    """{symbol: bucket} for the log's currently-open work."""
    import json
    r = subprocess.run([sys.executable, INDEX, "--json"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        return None
    out = {}
    for bucket, syms in json.loads(r.stdout)["open"].items():
        for s in syms:
            out[s] = bucket
    return out


def main(argv):
    known = {"--list", "--status", "--unwitnessed", "--bucket", "--regressions"}
    args = [a for a in argv[1:] if a.startswith("--")]
    syms = [a for a in argv[1:] if not a.startswith("--")]
    for a in args:
        if a not in known:
            print(f"check_symbol: unknown flag {a!r}", file=sys.stderr)
            return 2

    if "--regressions" in args:
        # exit 0 iff every CLOSED symbol's work is still in the tree.
        if not CLOSED:
            print("check_symbol: REFUSED — no closed symbol has a witness; the check "
                  "is vacuous, not the closures intact", file=sys.stderr)
            return 2
        gone = [s for s in sorted(CLOSED) if not CLOSED[s][1]()]
        # a LOST entry whose artifact has REAPPEARED is a stale status: refuse it
        stale = [s for s in sorted(LOST) if not LOST[s][1]()]
        if gone or stale:
            print(f"check_symbol: REGRESSED — {len(gone)} of {len(CLOSED)} closed "
                  f"symbol(s) no longer have their work in the tree"
                  + (f"; {len(stale)} LOST entr(y/ies) whose build is back and must move to CLOSED"
                     if stale else "") + ":", file=sys.stderr)
            for s in gone:
                print(f"    {s}: {CLOSED[s][0]}", file=sys.stderr)
            for s in stale:
                print(f"    {s}: LOST says '{LOST[s][0]}' but the artifact exists", file=sys.stderr)
            return 1
        print(f"check_symbol: {len(CLOSED)} of {len(CLOSED)} witnessed closed symbols still "
              f"re-derive from the tree; {len(LOST)} closed symbol(s) KNOWN-LOST"
              + (", named:" if LOST else ""))
        for s in sorted(LOST):
            print(f"    {s}: {LOST[s][0]} → {LOST[s][2]}")
        return 0

    if "--bucket" in args:
        # exit 0 iff EVERY witnessed symbol in this bucket is present.
        # ⚑ THE BUCKET IS THE LOG'S OWN UNIT, so a claim per bucket tracks the
        # log's structure rather than imposing one. Per-symbol detail is --status.
        if len(syms) != 1:
            print("check_symbol: --bucket needs exactly one bucket name",
                  file=sys.stderr)
            return 2
        want = syms[0].upper().replace("_", " ")
        opn = open_symbols()
        if opn is None:
            print("check_symbol: REFUSED — the index would not run", file=sys.stderr)
            return 2
        members = sorted(s for s, b in opn.items()
                         if b.upper() == want and s in WITNESS)
        if not members:
            print(f"check_symbol: REFUSED — no witnessed symbol in bucket {want!r}; "
                  f"the bucket is empty, renamed, or unwitnessed", file=sys.stderr)
            return 2
        openv = [s for s in members if not WITNESS[s][1]()]
        if openv:
            print(f"check_symbol: {want} — {len(openv)} of {len(members)} open:",
                  file=sys.stderr)
            for s in openv:
                print(f"    {s}: {WITNESS[s][0]}", file=sys.stderr)
            return 1
        print(f"check_symbol: {want} — {len(members)} of {len(members)} present")
        return 0

    if "--list" in args:
        for s, (what, _) in sorted(WITNESS.items()):
            print(f"{s}\t{what}")
        for s, (what, _) in sorted(CLOSED.items()):
            print(f"{s}\t(closed) {what}")
        return 0

    opn = open_symbols()
    if opn is None:
        print("check_symbol: REFUSED — the index would not run", file=sys.stderr)
        return 2

    if "--unwitnessed" in args:
        # LIVE is operator-blocked BY DESIGN, so it is not a gap.
        gaps = sorted(s for s, b in opn.items()
                      if b != "LIVE" and s not in WITNESS
                      and s not in UNWITNESSABLE)
        for s in gaps:
            print(f"{s}\t{opn[s]}")
        for s, why in sorted(UNWITNESSABLE.items()):
            print(f"{s}\t(by design) {why}")
        return 0

    if "--status" in args:
        for s in sorted(WITNESS):
            what, pred = WITNESS[s]
            state = "done" if pred() else "open"
            print(f"{state:5} {s:26} {opn.get(s, '(not in the open set)')}")
        return 0

    if not syms:
        print("check_symbol: name a symbol, or use --list / --status / --unwitnessed",
              file=sys.stderr)
        return 2
    rc = 0
    for s in syms:
        key = s if s.startswith("⊕") else "⊕" + s
        if key not in WITNESS:
            print(f"check_symbol: REFUSED — no witness for {key}. Operator-blocked "
                  f"work has none BY DESIGN; anything else is a gap to fill.",
                  file=sys.stderr)
            rc = max(rc, 2)
            continue
        what, pred = WITNESS[key]
        if pred():
            print(f"check_symbol: {key} — present ({what})")
        else:
            print(f"check_symbol: {key} — OPEN: {what}", file=sys.stderr)
            rc = max(rc, 1)
    return rc


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    check("every witness carries a description",
          all(w and callable(p) for w, p in WITNESS.values()), True)
    check("every description cites a log line",
          all(re.search(r":\d+\)", w) for w, _ in WITNESS.values()), True)
    opn = open_symbols()
    check("the index answers", opn is not None, True)
    if opn:
        # ⚑ NO NON-LIVE OPEN SYMBOL MAY LACK A WITNESS. That is the migration
        # being complete: prose became predicate for everything a check CAN
        # reach, and the rest is honestly operator-blocked.
        gaps = sorted(s for s, b in opn.items() if b != "LIVE"
                      and s not in WITNESS and s not in UNWITNESSABLE)
        check(f"no unwitnessed non-LIVE open symbol ({gaps})", gaps, [])
        check("every unwitnessable symbol states why",
              all(UNWITNESSABLE.values()), True)
        check("unwitnessable and witnessed are disjoint",
              sorted(set(UNWITNESSABLE) & set(WITNESS)), [])
        # ⚑ AND NO WITNESS FOR OPERATOR-BLOCKED WORK: a green check there would
        # be an unfalsifiable claim wearing a checkmark.
        live = sorted(s for s, b in opn.items() if b == "LIVE" and s in WITNESS)
        check(f"no witness claims LIVE work ({live})", live, [])
    # ⚑ THE CLOSED WITNESSES MUST BE ABLE TO SEE THE REGRESSION THEY EXIST FOR.
    # Synthetic QML, not the tree: equal strokes, and a bloom that is a wider
    # opaque copy rather than a blur (the recovered state of 2026-09-21).
    equal = ("property real strokeLit: segThick * (1 + 0.25 * weight)\n"
             "property real strokeGhost: segThick * (1 + 0.25 * weight)\n")
    weighted = ("property real strokeLit: segThick * (1 + 0.25 * weight)\n"
                "property real strokeGhost: segThick * (1 - 0.19 * weight)\n")
    check("equal strokes are not stroke-weight", _stroke_ratio(equal), 1.0)
    check("weighted strokes measure > 1", round(_stroke_ratio(weighted), 2), 1.54)
    check("no stroke properties is None", _stroke_ratio("Item {}"), None)
    fake_bloom = "Rectangle { opacity: 0.18; width: thick * 2.1; color: root.litColor }"
    real_bloom = ("Item {\n  layer.enabled: root.bloom > 0\n  layer.effect: MultiEffect {"
                  " blurEnabled: true }\n  Rectangle { color: root.litColor }\n}")
    ghost_bloom = ("Item {\n  layer.enabled: root.bloom > 0\n  layer.effect: MultiEffect {"
                   " blurEnabled: true }\n  Rectangle { color: root.ghostColor }\n}")
    check("a wider opaque copy is not a bloom", _bloom_is_blur(fake_bloom), False)
    check("a blurred lit-only layer is", _bloom_is_blur(real_bloom), True)
    check("a blurred layer that draws the ghost is not", _bloom_is_blur(ghost_bloom), False)
    check("closed witnesses cite a log line",
          all(re.search(r":\d+\)", w) for w, _ in CLOSED.values()), True)
    check("closed and open witnesses are disjoint", sorted(set(CLOSED) & set(WITNESS)), [])
    check("closed and lost are disjoint", sorted(set(CLOSED) & set(LOST)), [])
    check("every LOST entry names a rebuild waypoint", all(w.startswith("W") for _r, _p, w in LOST.values()), True)
    # ⚑ A LOST ENTRY MUST STILL BE LOST — otherwise it is the stale status this
    # repo forbids, one level up.
    back = [s for s, (_r, p, _w) in LOST.items() if not p()]
    check(f"every LOST build is still absent ({back})", back, [])
    # ⚑ AND THE COVERAGE: every symbol the index calls CLOSED that names an
    # artifact is either witnessed or known-lost. The design-log-only closures
    # (palette decisions, ⊕VER-* observations, naming) are listed so the gap is
    # a choice, not an omission.
    if opn is not None:
        import json as _json
        r = subprocess.run([sys.executable, INDEX, "--json"], capture_output=True, text=True, cwd=ROOT)
        closed_syms = {s for s, m in _json.loads(r.stdout)["symbols"].items() if m["closed"]}
        unaccounted = sorted(closed_syms - set(CLOSED) - set(LOST) - NO_ARTIFACT)
        check(f"every closed symbol is witnessed, known-lost, or listed as artifact-free ({unaccounted})",
              unaccounted, [])
    # every predicate must RUN without raising
    for s, (_w, p) in list(WITNESS.items()) + list(CLOSED.items()):
        try:
            p()
        except Exception as e:                      # noqa: BLE001
            check(f"{s} predicate runs", f"raised {e}", "ok")
    print("check_symbol selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
