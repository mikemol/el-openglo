#!/usr/bin/env python3
"""check_role_theme.py — the emitted role theme is SOLVED, and it actually loads.

Built for summit's `ask-cvd-graphviz-theme`. The ask wants role→colour as a data
artifact a consumer can bind to WITHOUT importing `cvd_gate` — which imports
`colorspacious` and `numpy`, so a consumer lacking those cannot reach the measured
palette at all.

    scripts/check_role_theme.py            # exit 0 iff the emitted theme is optimal and loads
    scripts/check_role_theme.py --emit     # print the artifacts
    scripts/check_role_theme.py --compare  # the solved assignment vs a consumer's live one
    scripts/check_role_theme.py --selftest

⚑ THE CHECK RENDERS THE .dot RATHER THAN ONLY PARSING IT, and that is not
belt-and-braces. The first version of `as_dot` emitted `edgecolor=` — an attribute
graphviz DOES NOT HAVE. The file parsed, `dot -Tsvg` would have exited 0, and every
edge would have rendered in the default black: a valid artifact that is silently
wrong, which is exactly the class this repo keeps catching by LOOKING rather than
by checking (a focus ring the colour of its own text, a foreground at 1.00:1, a
malformed 5x7 glyph). So the check asserts the colours SURVIVE INTO THE RENDER.

⚑ AND OPTIMALITY IS THE PROPERTY, NOT ADMISSIBILITY. Measured: all 2520 assignments
of 5 roles over the 7 Okabe-Ito members clear the floor, necessarily, because the
floor IS that palette's own tightest pair. A check asserting `q >= 1.0` would
therefore be UNFALSIFIABLE over this pool — it cannot fail, and paperkit's Δ grader
would call it vacuous. What can fail, and what this asserts, is that no other
assignment scores better.

⚑ THE WEAKNESS, STATED. This certifies the assignment is optimal FOR THE ROLES IT
WAS GIVEN under this metric. It says nothing about whether those are the right
roles, and nothing about whether a consumer should adopt it — a legend readers have
learned has value no metric can see, and substrate's live assignment clears the
floor comfortably at q=1.494. Optimal is not the same as owed.
"""
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cvd_gate as C                                              # noqa: E402
import role_theme as RT                                           # noqa: E402

# substrate's declared roles, SUPPLIED BY SUBSTRATE rather than read off its source.
#
# ⚑ I INFERRED TWO OF THESE WRONG AND THE CONSUMER CORRECTED BOTH.  I read
# `roundtrip` as deliberately sharing `flow`'s hue — its comment says weight and
# arrowhead carry the distinction — and pinned it. Substrate: the comment PREDATES
# the edge existing; roundtrip is now the heaviest edge in the graph and shares
# vermillion BY ACCIDENT of hand-assignment. Solve it free. Redundancy on top of a
# distinct hue, not instead of one.
#
# ⚑ AND `returns` IS A SIXTH ROLE I DID NOT SEE.  It takes `neutral` today — a
# local recessive colour, correctly OUTSIDE the palette. Measured before adopting
# it: six free roles cost 0.225 against the five-role optimum (q 1.719 -> 1.494)
# and still clear the floor comfortably, so `returns` gets a member and `neutral`
# RETIRES — one fewer colour outside the measured palette.
#
# A source read cannot recover intent. The roles are the consumer's to declare.
ROLES = ("read", "write", "pywrite", "flow", "roundtrip", "returns")
PINNED = {}

# The same consumer's LIVE assignment, for the comparison arm. Not a target — a
# measured starting point that clears the floor and is not optimal. `returns` is
# omitted because it currently carries `neutral`, which is not a palette member.
LIVE = {"read": "blue", "write": "bluegreen", "pywrite": "purple",
        "flow": "vermillion"}

# The emitted artifacts, named here rather than at a call site — the ask's witness
# scans the tree for a DATA file, so where these live is part of the answer.
ARTIFACT_DOT = "catalog/role-theme.dot"
ARTIFACT_JSON = "catalog/role-theme.json"

# ⚑ THE GROUNDED VARIANT IS A SECOND ARTIFACT, NOT A REPLACEMENT.  Substrate's six
# roles are INFEASIBLE on white (only 4 of 7 members clear 3:1), so it keeps five
# chromatic roles plus a declared off-palette `neutral` for `returns`. That set IS
# solvable, and emitting it separately is the honest form: the two files answer two
# different questions and a consumer picks by whether it draws strokes or regions.
# ⚑ AND FIVE FREE ROLES ON WHITE REFUSES TOO — I NEARLY EMITTED IT WITHOUT
# CHECKING.  Four eligible members cover four free roles, not five. The pinned form
# solves: `roundtrip` shares `vermillion` with `flow`, which is legitimate here for
# a reason substrate has now GATED in its own tree — a reused hue is allowed only
# while a distinct (style, penwidth, arrowhead, arrowtail) tuple carries the
# distinction the colour cannot.
#
# ⚑⚑ AND THE SOLVE LANDS EXACTLY ON SUBSTRATE'S LIVE ASSIGNMENT: blue, bluegreen,
# purple, vermillion, with roundtrip on vermillion. Its hand-picked set was the
# CONSTRAINED OPTIMUM all along — it had run this solve by hand without writing it
# down, and recorded the forced reuse as a free design choice. The artifact
# re-derives the decision from the outside, which is the only thing that could have
# caught a record that was wrong about a right answer.
GROUND = (255, 255, 255)
GROUND_ROLES = ("read", "write", "pywrite", "flow", "roundtrip")
GROUND_PINNED = {"roundtrip": "flow"}
ARTIFACT_GROUND_DOT = "catalog/role-theme-on-white.dot"
ARTIFACT_GROUND_JSON = "catalog/role-theme-on-white.json"


def solved():
    return RT.solve_roles(list(ROLES), pinned=dict(PINNED))


def solved_on_ground():
    """The same consumer's roles, constrained to be legible as strokes on white."""
    return RT.solve_roles(list(GROUND_ROLES), pinned=dict(GROUND_PINNED),
                          ground=GROUND)


def renders(dot_text):
    """(ok, detail) — does graphviz load it, and do the colours survive?

    A missing `dot` is a SKIP counted and printed: a fact about the machine, not
    about the artifact. NOT CONFIRMED IS NOT FAILED."""
    try:
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "theme.dot")
            with open(src, "w", encoding="utf-8") as fh:
                fh.write(dot_text)
            out = subprocess.run(["dot", "-Tsvg", src], capture_output=True,
                                 text=True, timeout=60)
    except FileNotFoundError:
        return None, "graphviz `dot` is not installed"
    except subprocess.TimeoutExpired:
        return False, "dot timed out"
    if out.returncode != 0:
        return False, f"dot exited {out.returncode}: {out.stderr.strip()[:200]}"
    return True, out.stdout


def problems():
    """[problem] — every way the emitted theme fails its own claims."""
    bad = []
    s = solved()

    # 1. every declared role is assigned, pinned ones included
    for r in ROLES:
        if r not in s["assignment"]:
            bad.append(f"role {r!r} is declared but unassigned")
    for role, target in PINNED.items():
        if s["colours"].get(role) != s["colours"].get(target):
            bad.append(f"{role!r} is pinned to {target!r} but carries a different colour")

    # 2. ⚑ OPTIMALITY, which is the falsifiable property here
    import itertools
    p = RT.pool()
    floors = C.reference_floors()
    free = [r for r in ROLES if r not in PINNED]
    for combo in itertools.permutations(sorted(p), len(free)):
        q, _ = RT.worst_pair({r: p[n] for r, n in zip(free, combo)}, floors)
        if q > s["worst_q"] + 1e-12:
            bad.append(f"a better assignment exists (q={q:.4f} > {s['worst_q']:.4f}): "
                       f"{dict(zip(free, combo))} — the emitted theme is not optimal")
            break

    # 3. the artifact must be parseable WITHOUT importing cvd_gate — the ask's point
    try:
        doc = json.loads(RT.as_json(s))
    except ValueError as e:
        bad.append(f"the emitted JSON does not parse: {e}")
        doc = {}
    for field in ("assignment", "roles", "worst_q", "metric", "solved_exhaustively"):
        if field not in doc:
            bad.append(f"the emitted JSON omits {field!r}, so a consumer cannot tell "
                       f"what was solved or how")
    for r in ROLES:
        v = doc.get("assignment", {}).get(r)
        if not (isinstance(v, str) and v.startswith("#") and len(v) == 7):
            bad.append(f"assignment[{r!r}] = {v!r} is not a #rrggbb hex")

    # 4. ⚑ THE GROUNDED VARIANT MUST ACTUALLY CLEAR ITS GROUND, or it is the same
    # silently-wrong artifact wearing a reassuring filename.
    try:
        g = solved_on_ground()
    except ValueError as e:
        bad.append(f"the grounded solve refuses: {e}")
        g = None
    if g is not None:
        if g.get("ground") != "#ffffff":
            bad.append(f"the grounded artifact records ground={g.get('ground')!r}, "
                       f"so a consumer cannot tell which objective it answers")
        for r, ratio in (g.get("ground_contrast") or {}).items():
            if ratio < 3.0:
                bad.append(f"grounded: {r} is {ratio}:1 against white, below the "
                           f"3:1 non-text minimum it claims to satisfy")
        # and the pin must hold — a reused hue is legitimate only as a DECLARED
        # constraint, never as a solve that quietly ran out of colours
        for role, target in GROUND_PINNED.items():
            if g["colours"].get(role) != g["colours"].get(target):
                bad.append(f"grounded: {role!r} is pinned to {target!r} and differs")

    # 5. ⚑ THE .dot MUST RENDER, NOT MERELY PARSE
    ok, detail = renders(RT.as_dot(s))
    if ok is None:
        pass                                     # SKIP — reported by the caller
    elif not ok:
        bad.append(f"the emitted .dot does not render: {detail}")
    else:
        for r in ROLES:
            hexv = RT._hex(s["colours"][r]).lower()
            if hexv not in detail.lower():
                bad.append(f"{r}'s colour {hexv} does not survive into the render — "
                           f"the file loads and the colour is not in it")
    return bad, s


def main(argv):
    known = {"--emit", "--write", "--compare", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_role_theme: unknown flag {a!r}", file=sys.stderr)
            return 2

    if "--emit" in argv:
        s = solved()
        print(RT.as_dot(s))
        print(RT.as_json(s), end="")
        return 0

    if "--write" in argv:
        # ⚑ WRITING THE ARTIFACT IS A MODE, NOT A SHELL ONE-LINER.  The first
        # attempt piped `python -c` into two `open().write()` calls, which the
        # no-chaining hook refused — correctly: a judgement about WHERE the theme
        # lives and WHAT it is named would have evaporated with the turn, and the
        # next reader would have re-derived it differently. The paths are here.
        s, g = solved(), solved_on_ground()
        out = []
        for name, text in ((ARTIFACT_DOT, RT.as_dot(s)),
                           (ARTIFACT_JSON, RT.as_json(s)),
                           (ARTIFACT_GROUND_DOT, RT.as_dot(g)),
                           (ARTIFACT_GROUND_JSON, RT.as_json(g))):
            path = os.path.join(ROOT, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            out.append(f"{name} ({len(text)} bytes)")
        print(f"check_role_theme: wrote {', '.join(out)}")
        return 0

    if "--compare" in argv:
        p = RT.pool()
        s = solved()
        live = {r: p[n] for r, n in LIVE.items()}
        lq, lb = RT.worst_pair(live)
        print(f"{'role':10s} {'live':12s} {'solved':12s}")
        for r in sorted(set(LIVE) | set(s["assignment"])):
            print(f"{r:10s} {LIVE.get(r, '-'):12s} {s['assignment'].get(r, '-'):12s}")
        print(f"\nlive   q={lq:.3f}  binding {lb[0]}~{lb[1]}")
        print(f"solved q={s['worst_q']:.3f}  binding "
              f"{s['binding_pair'][0]}~{s['binding_pair'][1]}")
        print(f"gap    {s['worst_q'] - lq:+.3f}  "
              f"(live is {100.0 * lq / s['worst_q']:.0f}% of achievable)")
        print("\n⚑ BOTH CLEAR THE FLOOR. The gap is optimality, not admissibility — "
              "and whether\n  it is worth changing a legend readers have learned is "
              "the consumer's call.")
        return 0

    if not ROLES:
        print("check_role_theme: REFUSED — no roles declared; the search is broken, "
              "not the theme optimal", file=sys.stderr)
        return 2

    bad, s = problems()
    ok, detail = renders(RT.as_dot(s))
    if bad:
        print(f"check_role_theme: REFUSED — {len(bad)} problem(s) over "
              f"{len(ROLES)} role(s):", file=sys.stderr)
        for b in bad:
            print(f"    {b}", file=sys.stderr)
        return 1
    skip = "" if ok else "  (SKIP: graphviz absent, render unverified)"
    print(f"check_role_theme: {len(ROLES)} of {len(ROLES)} roles assigned optimally "
          f"(q={s['worst_q']:.3f}, floor {s['floor_dE']:.1f}, exhaustive over "
          f"{len(RT.pool())} members){skip}")
    return 0


def _selftest():
    """Prove the check can SEE a theme that is admissible but not optimal."""
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    check("the emitted theme passes", main(["x"]), 0)
    check("problems() is empty on the real theme", problems()[0], [])

    # ⚑ THE CONSUMER'S ASSIGNED COLOURS WERE ALREADY OPTIMAL, and the selftest says
    # so rather than asserting the flattering thing. An earlier version asserted the
    # solve STRICTLY BEATS the live assignment — true only under my two wrong
    # inferences (roundtrip pinned, returns omitted). Over substrate's actual six
    # roles the optimum EQUALS what it had hand-assigned for the four it assigned;
    # the solve's contribution is placing the two it had not.
    p = RT.pool()
    live = {r: p[n] for r, n in LIVE.items()}
    lq, _ = RT.worst_pair(live)
    s_now = solved()
    check("the live assignment clears the floor", lq >= 1.0, True)
    check("the solve is at least as good", s_now["worst_q"] >= lq - 1e-12, True)
    check("the solve places the roles live did not",
          sorted(set(s_now["assignment"]) - set(LIVE)), ["returns", "roundtrip"])
    # ⚑ AND THE SOLVE DOES MOVE COLOURS, which I asserted it did not.  I wrote an
    # arm claiming the live colours SURVIVE into the solve; it failed on its first
    # run — `pywrite` moves purple->orange and `flow` vermillion->sky, and only
    # `read` and `write` hold. So the honest statement is that the SCORE is equal
    # while the ASSIGNMENT differs: two roles were reassigned to make room for the
    # two that had no palette member, at no cost to the worst pair. Recorded as an
    # arm rather than dropped, because the wrong version passed my reading and only
    # failed when run.
    moved = sorted(r for r, n in LIVE.items()
                   if r in s_now["assignment"] and s_now["assignment"][r] != n)
    check("the solve reassigns exactly pywrite and flow", moved, ["flow", "pywrite"])

    # ⚑ THE FIXTURE MUST COVER EVERY DECLARED ROLE, and my first one did not — it
    # built an assignment from LIVE alone, omitting `returns`, so `as_dot` raised
    # KeyError and the selftest failed on its own construction rather than on the
    # subject. The same shape as the marquee fixture that omitted `focus`.
    saved = RT.solve_roles
    try:
        def _worse(roles, pinned=None, members=None, **kw):
            # ⚑ **kw, BECAUSE A STUB WITH A FROZEN SIGNATURE BREAKS ON THE NEXT
            # ARGUMENT.  This stub omitted `ground=` and raised TypeError the moment
            # the real function grew one — the selftest failing on its own fixture
            # rather than on the subject, for the third time in this session.
            s = saved(roles, pinned=pinned, members=members, **kw)
            # a deliberately worse assignment over ALL the declared roles: shove
            # two roles onto near neighbours so the worst pair drops.
            bad = dict(s["assignment"])
            bad["write"] = "bluegreen"
            bad["flow"] = "sky"
            bad["read"] = "blue"
            s["assignment"] = bad
            s["colours"] = {r: p[n] for r, n in bad.items()}
            s["worst_q"], s["binding_pair"] = RT.worst_pair(s["colours"])
            s["worst_q"] -= 0.5          # claim a score the assignment cannot support
            return s
        RT.solve_roles = _worse
        probs, _ = problems()
        check("sees a sub-optimal assignment",
              any("not optimal" in b for b in probs), True)
    finally:
        RT.solve_roles = saved

    # ⚑ THE GROUNDED VARIANT, AND ITS GATE MUST BITE.  The grounded solve is the
    # answer to a different question, and an artifact claiming a ground it does not
    # clear is the silently-wrong file wearing a reassuring filename.
    g = solved_on_ground()
    check("the grounded solve records its ground", g["ground"], "#ffffff")
    check("every grounded role clears 3:1",
          all(v >= 3.0 for v in g["ground_contrast"].values()), True)
    check("the grounded pin holds",
          g["colours"]["roundtrip"], g["colours"]["flow"])
    # ⚑ AND IT MUST REFUSE ONE ROLE FURTHER — five FREE roles over four eligible
    # members. I nearly emitted that without checking, which is why it is an arm.
    try:
        RT.solve_roles(list(GROUND_ROLES), ground=GROUND)
        check("five FREE roles on white refuse", "passed", "raised")
    except ValueError:
        check("five FREE roles on white refuse", "raised", "raised")

    saved_g = solved_on_ground
    try:
        globals()["solved_on_ground"] = lambda: dict(
            g, ground_contrast=dict(g["ground_contrast"], read=1.32))
        probs, _ = problems()
        check("sees a grounded role below its own floor",
              any("below the" in b and "3:1" in b for b in probs), True)
    finally:
        globals()["solved_on_ground"] = saved_g

    # ⚑ AND THE RENDER ARM MUST BITE ON A COLOUR THAT DOES NOT SURVIVE.
    # `edgecolor` is the exact mistake the first version shipped.
    bogus = 'graph g {\n  read [edgecolor="#0072b2"]\n}\n'
    r_ok, detail = renders(bogus)
    if r_ok is None:
        print("  SKIP render arm — graphviz absent")
    else:
        check("a bogus attribute still parses", r_ok, True)
        check("...but its colour is absent from the render",
              "#0072b2" not in (detail or "").lower(), True)

    print("check_role_theme selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
