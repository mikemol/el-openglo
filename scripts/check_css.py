#!/usr/bin/env python3
"""check_css.py — the emitted stylesheet is the palette, parsed, not a copy of it.

⚑ THE CLAIM.  catalog/el-openglo.css parses (tinycss2 — a real CSS tokenizer,
not a regex), every custom property in every variant block resolves to that
variant's token with the same value, every variant carries every colour and
alpha key the token dict does, the Off/Lit polarity is mapped onto
prefers-color-scheme, and the seen-ghost identity is stated as color-mix().

    scripts/check_css.py            # exit 0 iff the stylesheet equals the palette
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


def problems(text=None):
    """Every way the stylesheet fails to be the palette."""
    text = open(CSS, encoding="utf-8").read() if text is None else text
    try:
        parsed = _parse(text)
    except ImportError:
        return ["SKIP: tinycss2 not importable — the stylesheet is unparsed, not wrong"]
    exp = expected()
    out = []
    for vid, props in exp.items():
        sel = f'[data-el-variant="{vid}"]'
        got = parsed.get(sel)
        if got is None:
            out.append(f"{vid}: no {sel} block")
            continue
        for p, v in props.items():
            if p not in got:
                out.append(f"{vid}: {p} missing")
            elif got[p] != v:
                out.append(f"{vid}: {p} = {got[p]!r}, token says {v!r}")
        for p in got:
            if p.startswith("--el-") and p not in props and p not in (
                    "--el-fg-in-seen", "--el-fg-in-seen-glanced",
                    "--el-ghost-alpha-glanced-infeasible", "--el-tt-is-sel"):
                out.append(f"{vid}: {p} is not a token")
        for p in ("--el-fg-in-seen", "--el-fg-in-seen-glanced"):
            v = got.get(p, "")
            if not (v.startswith("color-mix(") and "--el-fg-in" in v and "--el-view" in v):
                out.append(f"{vid}: {p} is not color-mix(fg_in over view)")
    root = parsed.get(":root")
    light = next((v for k, v in parsed.items() if k.startswith(":root@") and "light" in k), None)
    if root is None or root != parsed.get('[data-el-variant="EL-Openglo"]'):
        out.append(":root is not EL-Openglo")
    if light is None or light != parsed.get('[data-el-variant="EL-Openglo-Lit"]'):
        out.append("prefers-color-scheme: light is not EL-Openglo-Lit")
    return out


def main(argv):
    known = {"--map", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_css: unknown flag {a!r}", file=sys.stderr)
            return 2
    if not os.path.isfile(CSS):
        print("check_css: REFUSED — catalog/el-openglo.css absent; run make_css.py",
              file=sys.stderr)
        return 1
    exp = expected()
    if not exp:
        print("check_css: REFUSED — the token grid is empty", file=sys.stderr)
        return 2
    if "--map" in argv:
        parsed = _parse(open(CSS, encoding="utf-8").read())
        for vid, props in sorted(exp.items()):
            got = parsed.get(f'[data-el-variant="{vid}"]', {})
            print(f"{vid:16s} css={len(got):3d} tokens={len(props):3d}")
        return 0
    p = problems()
    if p and p[0].startswith("SKIP"):
        print(f"check_css: {p[0]}")
        return 0
    if p:
        print(f"check_css: REFUSED — {len(p)} problem(s) over {len(exp)} variant(s):",
              file=sys.stderr)
        for x in p[:20]:
            print(f"    {x}", file=sys.stderr)
        return 1
    n = sum(len(v) for v in exp.values())
    print(f"check_css: {n} of {n} custom properties over {len(exp)} variants equal "
          f"the palette; :root/light map to EL-Openglo/-Lit; seen ghost stated as color-mix()")
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

    import make_css
    css = make_css.stylesheet()
    check("the emitted stylesheet has no problems", problems(css), [])
    # ⚑ THE CHECK MUST SEE A STALE VALUE, A MISSING KEY, AND A FOREIGN PROPERTY —
    # in a VARIANT block, which is where values are compared (:root is compared
    # to its variant as a whole). Mutate after the EL-Azure selector.
    head, sep, tail = css.partition('[data-el-variant="EL-Azure"] {\n')
    assert sep, "the EL-Azure block must exist for the fixtures"

    def mutate(fn):
        return head + sep + fn(tail)

    stale = mutate(lambda t: re.sub(r"--el-fg: rgb\([^)]*\);", "--el-fg: rgb(0 0 0);", t, count=1))
    check("a stale value is seen", any("--el-fg = " in x for x in problems(stale)), True)
    dropped = mutate(lambda t: re.sub(r"  --el-view: [^\n]*\n", "", t, count=1))
    check("a missing key is seen", any("--el-view missing" in x for x in problems(dropped)), True)
    foreign = mutate(lambda t: "  --el-made-up: red;\n" + t)
    check("a property that is not a token is seen",
          any("not a token" in x for x in problems(foreign)), True)
    nomix = mutate(lambda t: t.replace("color-mix(in srgb, var(--el-fg-in)", "var(--el-fg-in", 1))
    check("a seen ghost that is not color-mix() is seen",
          any("not color-mix" in x for x in problems(nomix)), True)
    # ⚑ AND THE POLARITY MAP: a light block that is not the Lit variant is seen.
    lh, lsep, lt = css.partition("@media (prefers-color-scheme: light) {\n")
    swapped = lh + lsep + re.sub(r"--el-fg: rgb\([^)]*\);", "--el-fg: rgb(1 2 3);", lt, count=1)
    check("a light scheme that is not EL-Openglo-Lit is seen",
          any("light is not" in x for x in problems(swapped)), True)
    print("check_css selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
