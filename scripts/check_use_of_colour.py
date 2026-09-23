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
parser: a painter written in a shape it does not split (a sink behind a helper function,
a predicate built at run time) is invisible until this learns it. The population is the
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


def measure_painter(src, fn, surface, file, components=frozenset()):
    """[case] for one painter: per CONDITION, its channels, split into colour and cues.
    Behind an aperture (see the module docstring) ctx.fillRect is an opacity sink."""
    toks = lex(src)
    body = function_body(toks, fn)
    if body is None:
        return None
    feed = aperture_feed(toks, body, components)
    sinks = dict(SINKS, **({"ctx.fillRect": "opacity"} if feed else {}))
    stmts = statements(body)
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


def measure():
    cases, withheld = [], []
    components = aperture_components(template_sources())
    for p in PAINTERS:
        path = os.path.join(ROOT, p["file"])
        got = measure_painter(open(path, encoding="utf-8").read(), p["function"], p["surface"], p["file"],
                              components) if os.path.isfile(path) else None
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
    m = measure()
    chk("the real tree measures every condition", len(m["cases"]), len(CONDITIONS))
    chk("the real tree finds ApertureField as an aperture", "ApertureField" in m["aperture_components"], True)
    chk("the real marquee painter is derived as aperture-fed",
        {(c["sampled_by"] or {}).get("component") for c in m["cases"]}, {"ApertureField"})
    print("check_use_of_colour selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv))
