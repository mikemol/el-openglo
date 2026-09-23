#!/usr/bin/env python3
"""check_css.py — the emitted stylesheet is the palette, parsed, not a copy of it.

⚑ THE CLAIM.  catalog/el-openglo.css parses (tinycss2 — a real CSS tokenizer,
not a regex), every custom property in every variant block resolves to that
variant's token with the same value, every variant carries every colour and
alpha key the token dict does, the Off/Lit polarity is mapped onto
prefers-color-scheme, and the seen-ghost identity is stated as color-mix().

    scripts/check_css.py            # the verdict, as opa_gate css decides it
    scripts/check_css.py --json     # the measurement policy/css.rego decides
    scripts/check_css.py --map      # variant -> property count, vs the token dict
    scripts/check_css.py --selftest

⚑ A STALE FILE IS THE DEFECT THIS EXISTS TO SEE.  The stylesheet is generated;
a palette re-solve that forgets to re-emit it leaves a file that parses, looks
right, and is wrong. So this compares VALUES, not presence.

WEAKNESS, STATED.  tinycss2 tokenizes; it does not evaluate. color-mix() is
checked for presence and its operands, not for what a browser resolves it to —
that is check_ghost_composite's arithmetic, stated here as an expression.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
CSS = os.path.join(ROOT, "catalog", "el-openglo.css")


def _parse(text):
    """{selector: {prop: value}} via tinycss2, plus the light-scheme :root block
    under the pseudo-selector ':root@light'. Raises if tinycss2 is absent."""
    import tinycss2
    out = {}

    def decls(prelude_tokens, content):
        sel = tinycss2.serialize(prelude_tokens).strip()
        props = {}
        for d in tinycss2.parse_declaration_list(content, skip_whitespace=True,
                                                 skip_comments=True):
            if d.type == "declaration":
                props[d.name] = tinycss2.serialize(d.value).strip()
        return sel, props

    for rule in tinycss2.parse_stylesheet(text, skip_whitespace=True, skip_comments=True):
        if rule.type == "qualified-rule":
            sel, props = decls(rule.prelude, rule.content)
            out[sel] = props
        elif rule.type == "at-rule" and rule.at_keyword == "media":
            media = tinycss2.serialize(rule.prelude).strip()
            for inner in tinycss2.parse_rule_list(rule.content, skip_whitespace=True,
                                                  skip_comments=True):
                if inner.type == "qualified-rule":
                    sel, props = decls(inner.prelude, inner.content)
                    out[f"{sel}@{media}"] = props
    return out


def expected():
    """{variant_id: {prop: value}} — what make_css would emit, from the tokens."""
    import make_css
    out = {}
    for vid, t in make_css.tokens().items():
        props = {}
        for key, v in t.items():
            if make_css._is_rgb(v):
                r, g, b = (p.strip() for p in str(v).split(","))
                props[make_css._prop(key)] = f"rgb({r} {g} {b})"
            elif key in ("ghost_alpha", "ghost_alpha_glanced"):
                props[make_css._prop(key)] = f"{float(v):.3f}"
        out[vid] = props
    return out


def measure(text=None):
    """The MEASUREMENT policy/css.rego decides (W50): whether the sheet exists;
    per variant, the properties the token dict implies (`expected`) and the ones
    its [data-el-variant] block carries once parsed (`got`, None if no block);
    the parsed :root and prefers-color-scheme: light blocks. tinycss2 absent is
    `parsed: false` — the sheet is unparsed, not wrong. A stale value, a missing
    key, a foreign property, a non-color-mix seen ghost and a polarity that is
    not EL-Openglo/-Lit are defects by the policy's ruling, not here."""
    present = text is not None or os.path.isfile(CSS)
    exp = expected()
    out = {"file_present": present, "parsed": False, "root": None, "light": None,
           "cases": [{"id": vid, "expected": props, "got": None} for vid, props in exp.items()]}
    if not present:
        return out
    text = open(CSS, encoding="utf-8").read() if text is None else text
    try:
        parsed = _parse(text)
    except ImportError:
        return out
    out["parsed"] = True
    for c in out["cases"]:
        c["got"] = parsed.get(f'[data-el-variant="{c["id"]}"]')
    out["root"] = parsed.get(":root")
    out["light"] = next((v for k, v in parsed.items() if k.startswith(":root@") and "light" in k), None)
    return out


def main(argv):
    known = {"--map", "--selftest", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_css: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        import json
        print(json.dumps(measure(), indent=1))
        return 0
    if "--map" in argv:
        m = measure()
        for c in sorted(m["cases"], key=lambda c: c["id"]):
            got = "ABSENT" if c["got"] is None else f"{len(c['got']):3d}"
            print(f"{c['id']:16s} css={got} tokens={len(c['expected']):3d}")
        return 0
    import opa_gate
    return opa_gate.gate("css")


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    try:
        import tinycss2  # noqa: F401
    except ImportError:
        print("  SKIP tinycss2 not importable — the measurement cannot parse here")
        print("check_css selftest: SKIP")
        return True
    import make_css
    css = make_css.stylesheet()

    def azure(text):
        return next(c["got"] for c in measure(text)["cases"] if c["id"] == "EL-Azure")

    m = measure(css)
    check("the emitted stylesheet parses into every variant block",
          (m["parsed"], all(c["got"] is not None for c in m["cases"])), (True, True))
    # ⚑ THE MEASUREMENT MUST SEE A STALE VALUE, A MISSING KEY, A FOREIGN PROPERTY,
    # A NON-color-mix GHOST (W50: that each is a defect is policy/css_test.rego's
    # ruling) — in a VARIANT block. Mutate after the EL-Azure selector.
    head, sep, tail = css.partition('[data-el-variant="EL-Azure"] {\n')
    assert sep, "the EL-Azure block must exist for the fixtures"

    def mutate(fn):
        return head + sep + fn(tail)

    stale = mutate(lambda t: re.sub(r"--el-fg: rgb\([^)]*\);", "--el-fg: rgb(0 0 0);", t, count=1))
    check("a stale value is measured", azure(stale)["--el-fg"], "rgb(0 0 0)")
    dropped = mutate(lambda t: re.sub(r"  --el-view: [^\n]*\n", "", t, count=1))
    check("a missing key is measured as absent", "--el-view" in azure(dropped), False)
    foreign = mutate(lambda t: "  --el-made-up: red;\n" + t)
    check("a foreign property is measured", azure(foreign).get("--el-made-up"), "red")
    nomix = mutate(lambda t: t.replace("color-mix(in srgb, var(--el-fg-in)", "var(--el-fg-in", 1))
    check("a seen ghost without color-mix() is measured as such",
          azure(nomix)["--el-fg-in-seen"].startswith("color-mix("), False)
    # ⚑ AND THE POLARITY MAP: the light block is measured as what it carries.
    lh, lsep, lt = css.partition("@media (prefers-color-scheme: light) {\n")
    swapped = lh + lsep + re.sub(r"--el-fg: rgb\([^)]*\);", "--el-fg: rgb(1 2 3);", lt, count=1)
    check("a changed light scheme is measured", measure(swapped)["light"]["--el-fg"], "rgb(1 2 3)")
    print("check_css selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
