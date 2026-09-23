#!/usr/bin/env python3
"""check_use_of_colour.py — MEASURE, per state a painter shows, which channels carry it (W72).

WCAG 2.2 SC 1.4.1: colour must not be the ONLY visual means of conveying information.
⚑ Operator ruling 2026-09-23: opacity is colour too ("the dimmed notifications are
annoying, and probably fail A11y needs") — a state shown by hue or by alpha alone fails
alike. The design and census are catalog/use-of-colour.md.

The measurement is the design's "same predicate" test (mat230's same-row test, made
structural). For a PAINTER (a JS function in a QML template that draws with a 2D context)
it lexes the function body into statements and, per CONDITION (a state predicate such as
`urgency === 2`), follows the predicate through the variables it taints to the SINKS it
reaches. Each sink is a channel:

    ctx.fillStyle   hue       (colour)
    ctx.globalAlpha opacity   (colour, by the ruling)
    ctx.fillRect    weight    (the predicate changes the dot's size)
    on              shape     (the predicate lights a dot the glyph does not: a row)
    Alias.helper()  text      (W74: the subject handed to a case-changing helper in an
                               imported JS, at an argument the helper tests against the
                               condition's literal — see case_helpers)
    root.<p>        animation (W74: the predicate gates a read of a property an
                               Animation in the file writes — the critical flash)

An alias of the predicate's subject is found structurally too: a variable assigned from
`root.urgencyAt(...)` IS an urgency, whatever it is named (the gauge calls it `u0`).

⚑ THE SINK DEPENDS ON WHO READS THE CANVAS (W72.h, measured from pixels: low~normal
footprint 1.007-1.045 on all six variants — the "light dot" was not lighter in SIZE).
A painter that draws into an APERTURE's backdrop is not what the eye sees; the aperture
samples it. templates/ApertureField.qml:179-180 fixes every dot's size from the pitch
and dotFill alone (`d = round(uPx * dotFill)`), and :190 sets its only varying output,
`opacity: parent.cov`, where :151 makes cov the fraction of the cell's s x s aperture
the backdrop ink covers. So behind an aperture a fillRect SIZE change renders as the
same dots at another OPACITY: ctx.fillRect is an opacity sink there, i.e. colour.
Whether a painter is aperture-fed is DERIVED, not listed: the painter's
`<id>.backdrop.getContext` names an instance `<id>` of a component that declares
`property alias backdrop` (found by scanning templates/ for it: an aperture component).

The lit-cell predicate `on` STAYS shape through the aperture: `if (!on) continue` skips
the fillRect, so an unlit cell puts NO ink in its aperture and its pip sits at the
ghost floor, while a lit one is covered — a row lit that is otherwise dark (the
critical underline) survives sampling as a different SET of lit pips, not a level.

    scripts/check_use_of_colour.py --json      # the measurement (policy/use_of_colour.rego decides)
    scripts/check_use_of_colour.py --list      # every condition's channels, then n of m with a non-colour cue
    scripts/check_use_of_colour.py --selftest  # the measurement can SEE a colour-only fixture

The requirement is policy/use_of_colour.rego, run through `scripts/opa_gate.py use_of_colour`.

WEAKNESS, STATED. It proves a cue EXISTS and shares the predicate; it does not prove the
cue is PERCEPTIBLE at panel size — a lit row may still be too faint or too small to
read. That is a PIXEL measurement's job (the urgency-cue render check drafted as
scripts/check_urgency_cues.py in another worktree; not on main), not a lexer's. The
aperture rule is also coarse in the other direction: a fillRect that GROWS past its
cell (bold's +s/2) spills ink into neighbouring apertures, which is partly spatial,
but this counts every size change behind an aperture as opacity. The lexer is a JS-token lexer, not a JS
parser: a painter written in a shape it does not split (a sink behind a helper the file
does not import as `import "x.js" as X`, a predicate built at run time) is invisible
until this learns it. The helper rule credits a CASE CHANGE reachable under the tested
literal; it does not prove that the literals map to DIFFERENT cases (normal and
critical are both upper case — critical's distinction is its flash and underline). The population is the
painters in PAINTERS; census rows the source cannot decide (delegated to a consumer, or
drawn by a style) are listed in WITHHELD by hand from catalog/use-of-colour.md, not
measured — they are reported so the exclusion is visible, never admitted.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SINKS = {"ctx.fillStyle": "hue", "ctx.globalAlpha": "opacity", "ctx.fillRect": "weight", "on": "shape"}
COLOUR_CHANNELS = {"hue", "opacity"}
ALIAS_SOURCES = {"root.urgencyAt": "urgency"}

# (id, meaning, subject, test) — subject is a token or an alias kind; test is ("==", n) or ("truthy",)
CONDITIONS = [
    ("C6", "critical urgency (urgency == 2)", "urgency", ("==", "2")),
    ("C7", "low urgency (urgency == 0)", "urgency", ("==", "0")),
    # W74: normal is a state too — upper case is ITS letterform, as lowercase is low's
    ("C18", "normal urgency (urgency == 1)", "urgency", ("==", "1")),
    ("C8", "suspended job (jobState == 2)", "run.jobState", ("==", "2")),
    ("C10", "bold run", "run.bold", ("truthy",)),
    ("C11", "link / underline run", "run.underline", ("truthy",)),
]

PAINTERS = [
    {"surface": "marquee", "file": "templates/marquee-main.qml", "function": "drawBackdrop"},
]

WITHHELD = [
    {"id": "C5", "file": "templates/sddm-main.qml", "reason": "focus cue drawn by the Controls style; needs a render"},
    {"id": "C12", "file": "templates/marquee-main.qml", "reason": "sender's coloured run: meaning delegated to the sender"},
    {"id": "C14", "file": "templates/taskswitch-main.qml", "reason": "minimised caption drawn by itemCaption; needs a read and a render"},
    {"id": "C15", "file": "make_schemes.py", "reason": "consumer-owned role (KDE negative/neutral/positive)"},
    {"id": "C16", "file": "make_gtk.py", "reason": "consumer-owned role (GTK error/warning/success)"},
    {"id": "C17", "file": "make_konsole.py", "reason": "consumer-owned role (program-chosen ANSI colour)"},
]

TOKEN = re.compile(r"""
    (?P<ws>\s+) | (?P<lc>//[^\n]*) | (?P<bc>/\*.*?\*/) |
    (?P<str>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*') |
    (?P<id>[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*) |
    (?P<num>\d+(?:\.\d+)?) |
    (?P<op>===|!==|==|!=|<=|>=|&&|\|\||<<|>>|\+=|-=|\*=|/=|[-+*/%<>=!?:,;(){}\[\].&|^~@#])
""", re.X | re.S)


def lex(src):
    """[(kind, text, line)] — comments and whitespace dropped."""
    out, pos, line = [], 0, 1
    while pos < len(src):
        m = TOKEN.match(src, pos)
        if not m:                                        # an unknown byte: a token of its own
            out.append(("op", src[pos], line))
            line += src[pos] == "\n"
            pos += 1
            continue
        k, t = m.lastgroup, m.group()
        if k not in ("ws", "lc", "bc"):
            out.append((k, t, line))
        line += t.count("\n")
        pos = m.end()
    return out


def function_body(toks, name):
    """The tokens between `function <name>(...) {` and its matching `}`; None if absent."""
    for i in range(len(toks) - 1):
        if toks[i][1] == "function" and toks[i + 1][1] == name:
            j = i + 2
            while j < len(toks) and toks[j][1] != "{":
                j += 1
            depth, start = 0, j + 1
            for k in range(j, len(toks)):
                depth += {"{": 1, "}": -1}.get(toks[k][1], 0)
                if depth == 0:
                    return toks[start:k]
    return None


def statements(body):
    """[(target, rhs_tokens, line)] — `var a = x, b = y`, `a = x`, `a += x`, `f(args)`.
    Split at `;` `{` `}` outside parentheses; a control header (`if (...)`, `for (...)`)
    is dropped, its body is not."""
    chunks, cur, depth = [], [], 0
    for t in body:
        if t[1] in "([":
            depth += 1
        elif t[1] in ")]":
            depth -= 1
        if depth == 0 and t[1] in (";", "{", "}"):
            if cur:
                chunks.append(cur)
            cur = []
            continue
        cur.append(t)
    if cur:
        chunks.append(cur)
    out = []
    for ch in chunks:
        while ch and ch[0][1] in ("if", "for", "while", "else"):    # strip a control header
            if ch[0][1] == "else":
                ch = ch[1:]
                continue
            d, k = 0, 1
            for k in range(1, len(ch)):
                d += {"(": 1, ")": -1}.get(ch[k][1], 0)
                if d == 0:
                    break
            ch = ch[k + 1:]
        if not ch:
            continue
        if ch[0][1] == "var":
            for decl in _split_top(ch[1:], ","):
                if len(decl) >= 2 and decl[1][1] == "=":
                    out.append((decl[0][1], decl[2:], decl[0][2]))
        elif len(ch) >= 2 and ch[0][0] == "id" and ch[1][1] in ("=", "+=", "-=", "*=", "/="):
            out.append((ch[0][1], ch[2:], ch[0][2]))
        elif len(ch) >= 2 and ch[0][0] == "id" and ch[1][1] == "(":
            out.append((ch[0][1], ch[2:-1], ch[0][2]))
    return out


def _split_top(toks, sep):
    parts, cur, d = [], [], 0
    for t in toks:
        d += {"(": 1, "[": 1, "{": 1, ")": -1, "]": -1, "}": -1}.get(t[1], 0)
        if d == 0 and t[1] == sep:
            parts.append(cur)
            cur = []
        else:
            cur.append(t)
    parts.append(cur)
    return parts


def _mentions(rhs, subjects, test, tainted):
    words = [t[1] for t in rhs]
    if any(w in tainted for w in words):
        return True
    for i, w in enumerate(words):
        if w not in subjects:
            continue
        if test[0] == "truthy":
            return True
        if i + 2 < len(words) and words[i + 1] in ("===", "==") and words[i + 2] == test[1]:
            return True
    return False


def aperture_components(sources):
    """{component name} — the QML files (name -> source) whose tokens declare
    `property alias backdrop`: a component that samples a canvas its owner draws into."""
    out = set()
    for name, src in sources.items():
        w = [t[1] for t in lex(src)]
        if any(w[i:i + 3] == ["property", "alias", "backdrop"] for i in range(len(w) - 2)):
            out.add(name)
    return out


def aperture_feed(toks, body, components):
    """{instance, component, line} when the painter draws into `<id>.backdrop` of an
    instance of an aperture component declared in the same file; else None."""
    ids = {}
    for i in range(len(toks) - 1):
        if toks[i][1] in components and toks[i + 1][1] == "{":
            depth = 0
            for k in range(i + 1, len(toks) - 2):
                depth += {"{": 1, "}": -1}.get(toks[k][1], 0)
                if depth == 0:
                    break
                if depth == 1 and toks[k][1] == "id" and toks[k + 1][1] == ":":
                    ids[toks[k + 2][1]] = toks[i][1]
                    break
    for t in body:
        head = t[1].split(".")
        if t[0] == "id" and len(head) >= 3 and head[1:3] == ["backdrop", "getContext"] and head[0] in ids:
            return {"instance": head[0], "component": ids[head[0]], "line": t[2]}
    return None


CASE_METHODS = ("toLowerCase", "toUpperCase", "toLocaleLowerCase", "toLocaleUpperCase")
ANIMATIONS = {"PropertyAction", "NumberAnimation", "PropertyAnimation", "SmoothedAnimation",
              "SpringAnimation", "ColorAnimation"}


def _functions(toks):
    """{name: (params, body tokens)} for every `function name(params) { ... }`."""
    out = {}
    for i in range(len(toks) - 2):
        if toks[i][1] == "function" and toks[i + 1][0] == "id" and toks[i + 2][1] == "(":
            j = i + 3
            params = []
            while j < len(toks) and toks[j][1] != ")":
                if toks[j][0] == "id":
                    params.append(toks[j][1])
                j += 1
            body = function_body(toks, toks[i + 1][1])
            if body is not None:
                out[toks[i + 1][1]] = (params, body)
    return out


def _call_args(toks, k):
    """The top-level argument token lists of the call whose name is toks[k]."""
    if k + 1 >= len(toks) or toks[k + 1][1] != "(":
        return None
    d = 0
    for m in range(k + 1, len(toks)):
        d += {"(": 1, ")": -1}.get(toks[m][1], 0)
        if d == 0:
            return _split_top(toks[k + 2:m], ",")
    return None


def case_helpers(js_src):
    """⚑ A SINK BEHIND A HELPER (W74; the weakness this lexer stated). The marquee's
    case transform lives in marquee-body.js, not in the painter: the painter calls
    `Body.glyphFor(font, ch, urgency)`, which calls glyphKey, which calls displayChar,
    which compares `urgency === 0 / 1 / 2` and lowercases or uppercases. This reads a
    companion JS STRUCTURALLY: per function, for each parameter, the literals it is
    compared to (`p === N`), and whether the function (or one it passes that parameter
    on to, transitively) changes CASE. Returns {fn: {param index: set(literals)}} for
    the case-changing functions only."""
    toks = lex(js_src)
    fns = _functions(toks)
    direct, calls, cases = {}, {}, {}
    for name, (params, body) in fns.items():
        words = [t[1] for t in body]
        cases[name] = any(w.split(".")[-1] in CASE_METHODS for w in words)
        direct[name] = {p: {words[i + 2] for i, w in enumerate(words[:-2])
                            if w == p and words[i + 1] in ("===", "==") and re.fullmatch(r"\d+", words[i + 2])}
                        for p in params}
        calls[name] = []                      # (callee, callee param index, our param)
        for k, t in enumerate(body):
            if t[0] == "id" and t[1] in fns and t[1] != name:
                for ai, arg in enumerate(_call_args(body, k) or []):
                    if len(arg) == 1 and arg[0][1] in params:
                        calls[name].append((t[1], ai, arg[0][1]))
    tests = {n: {params.index(p): set(v) for p, v in direct[n].items()} for n, (params, _) in fns.items()}
    changed = True
    while changed:                            # fixed point: tests and case flow up the calls
        changed = False
        for name, (params, _) in fns.items():
            for callee, ai, p in calls[name]:
                if cases[callee] and not cases[name]:
                    cases[name] = changed = True
                got = tests[callee].get(ai, set())
                mine = tests[name].setdefault(params.index(p), set())
                if not got <= mine:
                    mine |= got
                    changed = True
    return {n: {i: s for i, s in tests[n].items() if s} for n in fns if cases[n]}


def js_imports(toks):
    """{alias: file} for every `import "file.js" as Alias` in a QML token stream."""
    out = {}
    for i in range(len(toks) - 3):
        if toks[i][1] == "import" and toks[i + 1][0] == "str" and toks[i + 2][1] == "as":
            f = toks[i + 1][1][1:-1]
            if f.endswith(".js"):
                out[toks[i + 3][1]] = f
    return out


def animated_properties(toks):
    """{property} written by an ANIMATION in the file: `PropertyAction { property: "p" }`
    (and the other Animation types), or `<Animation> on p`. A predicate that reads
    `root.p` in the painter then varies with time: an animation channel."""
    out = set()
    for i in range(len(toks) - 2):
        if toks[i][1] in ANIMATIONS or toks[i][1] == "SequentialAnimation":
            if toks[i + 1][1] == "on" and toks[i + 2][0] == "id":
                out.add(toks[i + 2][1])
            if toks[i][1] in ANIMATIONS and toks[i + 1][1] == "{":
                d = 0
                for k in range(i + 1, len(toks) - 2):
                    d += {"{": 1, "}": -1}.get(toks[k][1], 0)
                    if d == 0:
                        break
                    if toks[k][1] == "property" and toks[k + 1][1] == ":" and toks[k + 2][0] == "str":
                        out.add(toks[k + 2][1][1:-1])
    return out


def measure_painter(src, fn, surface, file, components=frozenset(), companions=None):
    """[case] for one painter: per CONDITION, its channels, split into colour and cues.
    Behind an aperture (see the module docstring) ctx.fillRect is an opacity sink.
    `companions` ({file: source}) are the JS files the QML imports: a call into one of
    their case-changing helpers that passes the predicate's subject is a TEXT channel
    for every literal the helper tests that argument against (W74)."""
    toks = lex(src)
    body = function_body(toks, fn)
    if body is None:
        return None
    feed = aperture_feed(toks, body, components)
    sinks = dict(SINKS, **({"ctx.fillRect": "opacity"} if feed else {}))
    stmts = statements(body)
    helpers = {}
    for alias, f in js_imports(toks).items():
        if companions and f in companions:
            for name, tests in case_helpers(companions[f]).items():
                helpers[f"{alias}.{name}"] = tests
    animated = animated_properties(toks)
    aliases = {"urgency": {"urgency"}}
    for target, rhs, _ in stmts:
        for w in (t[1] for t in rhs):
            if w in ALIAS_SOURCES:
                aliases.setdefault(ALIAS_SOURCES[w], set()).add(target)
    cases = []
    for cid, meaning, subject, test in CONDITIONS:
        subjects = aliases.get(subject, {subject})
        if test[0] == "truthy" and subject == "run.underline":
            subjects = {subject, "run.link.length"}
        present = any(t[1] in subjects for _, rhs, _ in stmts for t in rhs)
        if not present:
            continue
        tainted, changed = set(), True
        while changed:                                   # fixed point over variables
            changed = False
            for target, rhs, _ in stmts:
                if target not in SINKS and target not in tainted and _mentions(rhs, subjects, test, tainted):
                    tainted.add(target)
                    changed = True
        channels = []
        for target, rhs, line in stmts:
            if target in sinks and _mentions(rhs, subjects, test, tainted):
                channels.append({"kind": sinks[target], "line": line, "via": target})
            # a case-changing helper handed the subject at an argument it tests
            # against this condition's literal: the letterform is the channel
            for k, t in enumerate(rhs):
                if t[1] in helpers and test[0] == "==":
                    for ai, arg in enumerate(_call_args(rhs, k) or []):
                        if len(arg) == 1 and arg[0][1] in subjects and test[1] in helpers[t[1]].get(ai, set()):
                            channels.append({"kind": "text", "line": line, "via": t[1]})
            # the predicate gating a read of an ANIMATED property: it varies in time
            if _mentions(rhs, subjects, test, set()) and any(
                    t[0] == "id" and t[1].startswith("root.") and t[1].split(".", 1)[1] in animated for t in rhs):
                channels.append({"kind": "animation", "line": line,
                                 "via": next(t[1] for t in rhs if t[0] == "id" and t[1].startswith("root.")
                                             and t[1].split(".", 1)[1] in animated)})
        lines = [ln for _, rhs, ln in stmts if any(t[1] in subjects for t in rhs)]
        cases.append({"id": cid, "surface": surface, "file": file, "line": min(lines),
                      "meaning": meaning, "predicate": sorted(subjects), "tainted": sorted(tainted),
                      "sampled_by": feed,
                      "colour": [c for c in channels if c["kind"] in COLOUR_CHANNELS],
                      "cues": [c for c in channels if c["kind"] not in COLOUR_CHANNELS]})
    return cases


def template_sources():
    d = os.path.join(ROOT, "templates")
    return {f[:-4]: open(os.path.join(d, f), encoding="utf-8").read()
            for f in sorted(os.listdir(d)) if f.endswith(".qml")}


def companion_sources():
    """{file name: source} for the JS a template may import beside it (templates/*.js)."""
    d = os.path.join(ROOT, "templates")
    return {f: open(os.path.join(d, f), encoding="utf-8").read() for f in sorted(os.listdir(d)) if f.endswith(".js")}


def measure():
    cases, withheld = [], []
    components = aperture_components(template_sources())
    companions = companion_sources()
    for p in PAINTERS:
        path = os.path.join(ROOT, p["file"])
        got = measure_painter(open(path, encoding="utf-8").read(), p["function"], p["surface"], p["file"],
                              components, companions) if os.path.isfile(path) else None
        if got is None:
            withheld.append({"id": p["surface"], "file": p["file"], "line": 0,
                             "reason": f"painter function {p['function']} not found"})
        else:
            cases += got
    withheld += [dict(w, line=0) for w in WITHHELD]
    return {"cases": cases, "withheld": withheld, "painters": len(PAINTERS),
            "conditions": len(CONDITIONS), "aperture_components": sorted(components)}


def main(argv):
    known = {"--json", "--list", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_use_of_colour: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    if "--list" in argv:
        m = measure()
        for c in m["cases"]:
            col = ",".join(sorted({x["kind"] for x in c["colour"]})) or "-"
            cue = ",".join(sorted({x["kind"] for x in c["cues"]})) or "NONE"
            via = f"  [sampled by {c['sampled_by']['instance']} ({c['sampled_by']['component']})]" \
                if c.get("sampled_by") else ""
            print(f"  {c['id']:4s} {c['file']}:{c['line']:<4d} colour={col:12s} cues={cue:14s} {c['meaning']}{via}")
        for w in m["withheld"]:
            print(f"  {w['id']:4s} {w['file']}  withheld: {w['reason']}")
        good = sum(bool(c["cues"]) for c in m["cases"])
        print(f"\ncheck_use_of_colour: {good} of {len(m['cases'])} condition(s) carry a non-colour cue "
              f"({len(m['cases'])} of {m['conditions']} conditions found over {m['painters']} painter(s)); "
              f"{len(m['withheld'])} withheld")
        return 0
    print("usage: check_use_of_colour.py --json | --list | --selftest  "
          "(the verdict: scripts/opa_gate.py use_of_colour)", file=sys.stderr)
    return 2


COLOUR_ONLY = """
function paint() {
    var u = root.urgencyAt(i);
    ctx.fillStyle = u === 2 ? hot : lit;
    ctx.globalAlpha = u === 0 ? 0.5 : 1.0;
    var grow = (run && run.bold) ? s / 2 : 0;
    ctx.fillRect(x - grow, y - grow, s + 2 * grow, s + 2 * grow);
}
"""
WITH_CUES = """
function paint() {
    var u = root.urgencyAt(i);
    ctx.fillStyle = u === 2 ? hot : lit;
    var grow = ((run && run.bold) ? s / 2 : 0) + (u === 2 ? s / 2 : u === 0 ? -s / 4 : 0);
    var under = u === 2;
    for (var r = 0; r < rows; r++) {
        var on = bit(r) || (under && r === rows - 1);
        if (!on) continue;
        ctx.fillRect(x - grow, y - grow, s + 2 * grow, s + 2 * grow);
    }
}
"""
# the SAME painter, drawing into an aperture's backdrop: its size changes become opacity
APERTURE_COMPONENT = "Item { property alias backdrop: bd\n Canvas { id: bd } }"
APERTURE_FED = """
Item {
    Pinholes { id: fld; rows: 8 }
    function paint() {
        var ctx = fld.backdrop.getContext("2d");
""" + WITH_CUES.split("function paint() {", 1)[1] + "}\n"


LETTERFORM_JS = """
function shown(ch, u) {
    var t = ch;
    if (u === 0) t = ch.toLowerCase();
    else if (u === 1 || u === 2) t = ch.toUpperCase();
    return t;
}
function outer(font, ch, u) { return font[shown(ch, u)]; }
"""
LETTERFORM = """
import "lf.js" as Lf
Item {
    SequentialAnimation { PropertyAction { target: root; property: "flashLit"; value: false } }
    Pinholes { id: fld; rows: 8 }
    function paint() {
        var ctx = fld.backdrop.getContext("2d");
        var u = root.urgencyAt(i);
        ctx.fillStyle = u === 2 ? hot : lit;
        var bytes = Lf.outer(font, ch, u);
        var dark = u === 2 && !root.flashLit;
        for (var r = 0; r < rows; r++) {
            var on = !dark && bit(bytes, r);
            if (!on) continue;
            ctx.fillRect(x, y, s, s);
        }
    }
}
"""


def _selftest():
    """The measurement can SEE: a colour-only fixture yields no cue for critical (hue)
    and low (opacity); the same painter with a weight and a row yields them; and the real
    tree's population is non-empty."""
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    def kinds(cases, cid, key):
        return sorted({x["kind"] for c in cases if c["id"] == cid for x in c[key]})

    bad = measure_painter(COLOUR_ONLY, "paint", "fixture", "fixture.qml")
    chk("colour-only: critical is hue, no cue", (kinds(bad, "C6", "colour"), kinds(bad, "C6", "cues")), (["hue"], []))
    chk("colour-only: low is opacity, no cue", (kinds(bad, "C7", "colour"), kinds(bad, "C7", "cues")), (["opacity"], []))
    chk("colour-only: bold is still weight", kinds(bad, "C10", "cues"), ["weight"])
    good = measure_painter(WITH_CUES, "paint", "fixture", "fixture.qml")
    chk("with cues: critical is weight + shape", kinds(good, "C6", "cues"), ["shape", "weight"])
    chk("with cues: low is weight, no opacity", (kinds(good, "C7", "colour"), kinds(good, "C7", "cues")), ([], ["weight"]))
    chk("an absent painter is None", measure_painter(COLOUR_ONLY, "nope", "f", "f"), None)
    comps = aperture_components({"Pinholes": APERTURE_COMPONENT, "Plain": "Item { Canvas { id: c } }"})
    chk("an aperture component is found by its backdrop alias", comps, {"Pinholes"})
    fed = measure_painter(APERTURE_FED, "paint", "fixture", "fixture.qml", comps)
    chk("behind an aperture: the feed is derived", fed[0]["sampled_by"]["instance"], "fld")
    chk("behind an aperture: low's shrink is opacity, no cue",
        (kinds(fed, "C7", "colour"), kinds(fed, "C7", "cues")), (["opacity"], []))
    chk("behind an aperture: critical keeps the lit row (shape), weight gone",
        kinds(fed, "C6", "cues"), ["shape"])
    chk("without the component known, the same painter is not aperture-fed",
        kinds(measure_painter(APERTURE_FED, "paint", "f", "f"), "C7", "cues"), ["weight"])
    # W74: a case transform behind a helper in an imported JS, and a flash
    lf = measure_painter(LETTERFORM, "paint", "fixture", "fixture.qml", comps, {"lf.js": LETTERFORM_JS})
    chk("a case helper handed the urgency is TEXT for low, normal and critical",
        [kinds(lf, cid, "cues") for cid in ("C7", "C18", "C6")], [["text"], ["text"], ["animation", "shape", "text"]])   # the dark phase gates `on`: shape too
    flat = measure_painter(LETTERFORM, "paint", "fixture", "fixture.qml", comps,
                           {"lf.js": LETTERFORM_JS.replace("ch.toLowerCase()", "ch").replace("ch.toUpperCase()", "ch")})
    chk("...the same helper WITHOUT a case change is no cue (low and normal)",
        (kinds(flat, "C7", "cues"), kinds(flat, "C18", "cues")), ([], []))
    chk("...and the helper is found only through the import (no companions: no cue)",
        kinds(measure_painter(LETTERFORM, "paint", "f", "f", comps), "C7", "cues"), [])
    chk("the flash is found from the PropertyAction that writes the property",
        animated_properties(lex(LETTERFORM)), {"flashLit"})
    chk("helper tests flow up the call chain (outer(font, ch, u) -> shown(ch, u))",
        case_helpers(LETTERFORM_JS)["outer"], {2: {"0", "1", "2"}})
    m = measure()
    chk("the real tree measures every condition", len(m["cases"]), len(CONDITIONS))
    chk("the real tree finds ApertureField as an aperture", "ApertureField" in m["aperture_components"], True)
    chk("the real marquee painter is derived as aperture-fed",
        {(c["sampled_by"] or {}).get("component") for c in m["cases"]}, {"ApertureField"})
    print("check_use_of_colour selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv))
