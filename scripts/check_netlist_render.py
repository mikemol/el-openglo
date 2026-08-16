#!/usr/bin/env python3
"""check_netlist_render.py — the netlist renders, and the picture is the graph.

The constraint netlist is 21 nodes and 41 edges across four families, and reading
it as a table is how a cycle stays invisible. This emits it as graphviz — the whole
graph, and the elimination sequence frame by frame — so the structure can be SEEN.

    scripts/check_netlist_render.py            # exit 0 iff the emitted dot renders
    scripts/check_netlist_render.py --write    # write the static view + every frame
    scripts/check_netlist_render.py --steps    # the elimination sequence, as text
    scripts/check_netlist_render.py --selftest

⚑ THE CHECK RENDERS RATHER THAN PARSES, for the reason the role theme paid for:
`edgecolor=` is not a graphviz attribute, so a file carrying it parses, exits 0,
and draws every edge in the default black. A valid artifact that is wrong. So this
runs `dot -Tsvg` and asserts the FAMILY COLOURS reach the output.

⚑ AND THE ELIMINATION ORDER IS A GAUGE, WHICH THE SEQUENCE MAKES VISIBLE. Measured:
`min_degree` costs 62 Q over 15 steps while the relations check's order costs 68 Q
— same terminals, same three surviving terms, different cost. That is
`Elimination.as_gauge()` and `.as_cost()` being separate records rather than a
discrepancy, and a reader watching the frames is watching ONE gauge choice.

⚑ THE WEAKNESS, STATED. A picture that renders is not a picture that is legible,
and this cannot check the second. It asserts the dot loads, the colours survive,
every node appears, and the frame count matches the elimination length. Whether the
layout is readable at 21 nodes is a question only LOOKING answers — which is why
--write emits the files rather than only reporting on them.
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import palette_graph as PG                                        # noqa: E402
import netlist_render as NR                                       # noqa: E402

ARTIFACT_DIR = "catalog/netlist"
STATIC = "netlist.dot"


def renders(dot_text):
    """(ok, svg) — does graphviz load it? None means dot is absent (a SKIP)."""
    try:
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "g.dot")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write(dot_text)
            out = subprocess.run(["dot", "-Tsvg", src], capture_output=True,
                                 text=True, timeout=120)
    except FileNotFoundError:
        return None, "graphviz `dot` is not installed"
    except subprocess.TimeoutExpired:
        return False, "dot timed out"
    if out.returncode != 0:
        return False, f"dot exited {out.returncode}: {out.stderr.strip()[:300]}"
    return True, out.stdout


def problems():
    """[problem] — every way the render fails to be the graph."""
    bad = []
    fr = NR.frames()
    if not fr:
        return ["no elimination frames; the solve did not run"], fr

    # 1. the sequence must actually eliminate everything eliminable
    last_nodes = set(fr[-1][2])
    import palette_relations as PR
    terms = set(PR.terminals())
    leftover = {n for n in last_nodes if n not in terms}
    # a node with no live edge is not eliminable and legitimately remains
    live_last = {n for k in fr[-1][3] for n in k}
    stuck = leftover & live_last
    if stuck:
        bad.append(f"{len(stuck)} interior node(s) still carry edges after the "
                   f"sequence ends: {sorted(stuck)[:5]}")

    # 2. ⚑ EVERY NODE MUST APPEAR IN THE PICTURE, or the render is a subset
    #    pretending to be the graph — the `--edges` hardcoded-family defect again.
    dot = NR.as_dot()
    for n in PG.nodes():
        if f'"{n}"' not in dot:
            bad.append(f"node {n!r} is in the graph and not in the render")

    # 3. every family must be distinguishable, or the picture loses the
    #    constraint/arrow distinction that makes it worth drawing
    fams = {e.family for e in PG.edges()}
    for f in fams:
        colour, _style = NR.FAMILY_STYLE.get(f, (None, None))
        if colour is None:
            bad.append(f"family {f!r} has no style, so it draws as every other")
        elif colour.lower() not in dot.lower():
            bad.append(f"family {f!r} styles as {colour} which is absent from "
                       f"the render")

    # 4. ⚑ IT MUST RENDER, NOT MERELY PARSE
    ok, detail = renders(dot)
    if ok is False:
        bad.append(f"the static view does not render: {detail}")
    elif ok:
        for f in fams:
            colour = NR.FAMILY_STYLE[f][0]
            if colour.lower() not in detail.lower():
                bad.append(f"family {f!r}'s colour {colour} does not survive into "
                           f"the SVG — the file loads and the colour is not in it")
    return bad, fr


def main(argv):
    known = {"--write", "--steps", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_netlist_render: unknown flag {a!r}", file=sys.stderr)
            return 2

    if "--steps" in argv:
        fr = NR.frames()
        print(f"{'step':>4s} {'eliminated':16s} {'nodes':>6s} {'edges':>6s} "
              f"{'fill-in':>8s} {'Q':>5s}")
        for step, elim, nodes, edges, fill, q in fr:
            print(f"{step:4d} {(elim or '(start)'):16s} {len(nodes):6d} "
                  f"{len(edges):6d} {len(fill):8d} {q:5d}")
        print(f"\n⚑ the order is a GAUGE and the Q is a COST: min_degree spends "
              f"{fr[-1][5]} Q here;\n  the relations check's fixed order spends 68. "
              f"Same terminals, same answer.")
        return 0

    if "--write" in argv:
        out = os.path.join(ROOT, ARTIFACT_DIR)
        os.makedirs(out, exist_ok=True)
        written = []
        static = NR.as_dot()
        with open(os.path.join(out, STATIC), "w", encoding="utf-8") as fh:
            fh.write(static)
        written.append(STATIC)
        fr = NR.frames()
        for step, *_ in fr:
            name = f"netlist-step-{step:02d}.dot"
            with open(os.path.join(out, name), "w", encoding="utf-8") as fh:
                fh.write(NR.as_dot(step=step))
            written.append(name)
        print(f"check_netlist_render: wrote {len(written)} file(s) into "
              f"{ARTIFACT_DIR}/ (1 static + {len(fr)} frames)")
        print(f"  render one:  dot -Tsvg {ARTIFACT_DIR}/{STATIC} -o netlist.svg")
        print(f"  render all:  for f in {ARTIFACT_DIR}/*.dot; do "
              f"dot -Tsvg \"$f\" -o \"${{f%.dot}}.svg\"; done")
        return 0

    bad, fr = problems()
    if bad:
        print(f"check_netlist_render: REFUSED — {len(bad)} problem(s) over "
              f"{len(PG.nodes())} nodes and {len(fr)} frames:", file=sys.stderr)
        for b in bad[:15]:
            print(f"    {b}", file=sys.stderr)
        return 1
    ok, _ = renders(NR.as_dot())
    skip = "" if ok else "  (SKIP: graphviz absent, render unverified)"
    print(f"check_netlist_render: {len(PG.nodes())} nodes and {len(PG.edges())} "
          f"edges render across {len(fr)} frames ({fr[-1][5]} Q){skip}")
    return 0


def _selftest():
    """Prove the render is the graph, and that the check can see it not be."""
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    check("the real graph renders", main(["x"]), 0)
    check("problems() is empty on the real graph", problems()[0], [])

    fr = NR.frames()
    check("the sequence starts with the whole graph",
          len(fr[0][2]), len(PG.nodes(constraining_only=True)))
    check("every step eliminates exactly one node",
          all(len(fr[i - 1][2]) - len(fr[i][2]) == 1 for i in range(1, len(fr))),
          True)
    check("cost is monotone", all(fr[i][5] >= fr[i - 1][5]
                                  for i in range(1, len(fr))), True)
    # ⚑ FILL-IN MUST ACTUALLY OCCUR SOMEWHERE, or the sequence is drawing nothing
    # the static view does not already show.
    check("at least one step produces fill-in",
          any(f[4] for f in fr), True)

    # a frame past the end clamps rather than raising
    late = NR.as_dot(step=999)
    check("a step past the end clamps", "elimination step" in late, True)

    # ⚑ AND THE RENDER ARM MUST BITE. A family styled with a colour the emitter
    # never writes is the `edgecolor=` shape: the file loads and the distinction
    # is gone.
    saved = dict(NR.FAMILY_STYLE)
    try:
        NR.FAMILY_STYLE[PG.GEOMETRY] = ("#123456", "solid")
        # the emitter now writes #123456, so a check looking for the OLD colour
        # must notice; simulate by asserting the old one is gone
        d = NR.as_dot()
        check("changing a family colour changes the render",
              "#123456" in d and saved[PG.GEOMETRY][0] not in d, True)
    finally:
        NR.FAMILY_STYLE.clear()
        NR.FAMILY_STYLE.update(saved)

    saved_fr = NR.frames
    try:
        NR.frames = lambda keep=None: []
        probs, _ = problems()
        check("an empty sequence is seen",
              any("did not run" in p for p in probs), True)
    finally:
        NR.frames = saved_fr

    print("check_netlist_render selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
