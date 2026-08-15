"""role_theme — role→colour as a SOLVED assignment, emitted as data.

⚑ THE ASSIGNMENT IS ITSELF A MEASUREMENT, WHICH IS WHY A HEX LIST IS NOT THE
ANSWER.  Which palette member serves which semantic role is a separation problem
over the roles a consumer declares — exactly what `worst_view_dE` decides and
exactly what a hand assignment gets wrong.  A consumer handed seven hexes still
has to choose, and choosing is the part that needs the gate's metric.

Built for summit's `ask-cvd-graphviz-theme` (by substrate), and measuring its
premise first CORRECTED it in two places while making its conclusion stronger:

  * substrate had ALREADY stopped transcribing hexes — `pipeflow.py:_ok()`
    resolves from `cvd_gate` at runtime with a stamped fallback.  The "9 of 16
    pairs" in its own comment is the ORIGINAL hand-picked set that Okabe-Ito
    replaced, not the current state.
  * and picking FROM Okabe-Ito cannot fail the floor: all 2520 assignments of 5
    roles over the 7 members clear q >= 1.0, necessarily, because the floor IS
    this palette's own tightest pair (dE 11.0, orange~purple under tritanomaly).
    "A hand assignment might fail the gate" is the wrong argument.

⚑ THE RIGHT ARGUMENT IS OPTIMALITY, AND IT IS LARGE.  Substrate's live assignment
scores q = 1.494; the best available over the same pool is q = 2.758 — 54% of
achievable separation, with every gate green.  ADMISSIBILITY IS VISIBLE TO A
CHECKER; OPTIMALITY IS ONLY VISIBLE TO A SOLVE.  That gap is what this closes.

⚑ AN ASSIGNMENT OVER A FIXED POOL IS NOT A SECTOR SEARCH, and conflating them was
the first design error here.  `make_palette.solve_semantic_set` optimises the same
objective but GENERATES candidates by hue from a sector table; the pool here is
seven published colours and the question is which member serves which role.  Right
objective, wrong domain — so this reuses `_worst_normalized` and
`reference_floors` and emphatically NOT the candidate generator.

⚑ AND THE ROLES ARE AN ARGUMENT, NEVER OURS.  el-openglo's own roles are
neg/neu/pos/link/visited; substrate's are read/write/pywrite/flow; a third
consumer's will differ again.  A theme hardcoding our roles would be a bag of
hexes with extra steps.  `solve_roles` takes the consumer's declared roles, and
the emitted artifact CARRIES the role list it solved so a reader can see what was
assumed rather than infer it.
"""
from __future__ import annotations

import itertools
import json

import cvd_gate as C


def pool():
    """The Okabe-Ito chromatic members — the reference palette, not our palette.

    ⚑ DELIBERATELY THE PUBLISHED SET AND NOT el-openglo's SOLVED ACCENTS.  A
    consumer asking for a CVD-safe role theme wants a palette whose separation
    property is a published design result, not one solved for a desktop theme's
    hue seed.  Ours is downstream of a chosen identity; this is not."""
    return dict(C.OKABE_ITO)


_Q_CACHE = {}


def _q(a, b, floors):
    """The gate's normalised separation for one pair, memoised on the COLOURS.

    ⚑ THE POOL IS SMALL AND THE SWEEP IS NOT.  7P6 = 5040 assignments over 15
    pairs each is ~75k calls, but there are only 21 distinct colour pairs in a
    seven-member pool — so all but 21 of those calls recompute an answer already
    known. Uncached, the selftest TIMED OUT at 550s while the single check ran in
    seconds, which is `make_palette._DE_CACHE`'s lesson arriving in a second place:
    `worst_view_dE` runs a CVD simulation per view and is far too expensive to call
    inside a permutation loop.

    Keyed on the colour pair rather than the roles, because the same two colours
    score identically whatever roles hold them.

    ⚑ THE BOUND WAS HANDED TO ME AND HAS NEVER BEEN EXERCISED, WHICH IS LUCK AND
    NOT A MEASUREMENT.  21 entries is C(7,2) — a ceiling the seven-member pool
    imposes, not one this cache enforces. Nothing here tests what it does at scale
    because with this pool nothing CAN: it cannot grow past 21 no matter how many
    assignments are swept. Anyone widening the pool inherits an unbounded dict on a
    key space that grows quadratically, and should measure the memory rather than
    assume this line kept working.

    Recorded because substrate paid for the other half of this lesson in its own
    tree — a cache it added for speed OOM-killed its suite under a memory lease,
    and the suite VANISHED rather than failing. Its sharper statement, which
    applies to this cache too: a bound you did not push until it failed differently
    is not a measurement."""
    key = (a, b) if a <= b else (b, a)
    v = _Q_CACHE.get(key)
    if v is None:
        v = C._worst_normalized(a, b, floors)[0]
        _Q_CACHE[key] = v
    return v


def worst_pair(assignment, floors=None):
    """(q, (role_a, role_b)) — the gate's own metric over every assigned pair.

    ⚑ `_worst_normalized`, NOT RAW dE.  The gate normalises dE by the floor its
    pair class is judged against and fails below 1.0 in ANY CVD view, so a solver
    maximising raw distance optimises a proxy that diverges exactly at the margin.
    This is `make_palette`'s own ⊕SOLVER-BACKLIT-CVD result, reused rather than
    re-derived."""
    floors = floors or C.reference_floors()
    roles = list(assignment)
    m, binding = float("inf"), None
    for i in range(len(roles)):
        for j in range(i + 1, len(roles)):
            q = _q(assignment[roles[i]], assignment[roles[j]], floors)
            if q < m:
                m, binding = q, (roles[i], roles[j])
    return m, binding


def eligible(ground, floor=3.0, members=None):
    """Members clearing `floor` contrast against `ground` — the ground constraint.

    ⚑ MUTUAL DISTINCTNESS AND LEGIBILITY-ON-A-GROUND ARE TWO DIFFERENT OBJECTIVES,
    AND SOLVING ONE SAYS NOTHING ABOUT THE OTHER.  Filed by substrate against this
    module's first output: the assignment scored q=1.494, cleared the separation
    floor, and rendered THREE OF SIX EDGES NEARLY INVISIBLE as strokes on a white
    page — `yellow` at 1.32:1, `sky` at 2.31:1, `orange` at 2.25:1 against WCAG's
    3:1 non-text minimum. Verified here rather than relayed.

    The palette member did not change; the ROLE did, from region to line. `yellow`
    is a fine FILL with black text on it — which is how el-openglo uses it — and a
    near-invisible 1px stroke on white.

    ⚑ AND IT IS THE `edgecolor=` DEFECT ONE LEVEL UP, as substrate names it: an
    artifact that passes its own check and is wrong on the page it is for, found
    only by rendering. The separation floor has NO NOTION OF A GROUND, so it cannot
    see this and never could.

    `ground=None` means no ground was declared and every member is eligible — a
    consumer drawing filled regions is not lying by omission, it genuinely has no
    ground constraint."""
    members = members or pool()
    if ground is None:
        return dict(members)
    g = tuple(ground)
    return {n: c for n, c in members.items() if C.wcag_ratio(c, g) >= floor}


def solve_roles(roles, pinned=None, members=None, ground=None, ground_floor=3.0):
    """Assign palette members to `roles`, maximising the WORST pair's separation.

    `ground`, when given, restricts the pool to members clearing `ground_floor`
    contrast against it, so the assignment is legible AS A STROKE on that ground as
    well as mutually distinct.

    ⚑ AN INFEASIBLE GROUND IS A REFUSAL, NOT A WORSE ASSIGNMENT.  Measured: only 4
    of the 7 Okabe-Ito members clear 3:1 on white (blue, bluegreen, purple,
    vermillion), so substrate's six declared roles CANNOT all be placed. Returning
    a best-effort assignment there would hand back exactly the silently-wrong
    artifact this constraint exists to prevent — three roles below the floor, with
    a q-score that looks fine. The refusal names the deficit and the eligible set,
    because a consumer needs to know whether to drop a role, widen the pool, or
    accept an off-palette colour.

    `pinned` maps a role to another role whose colour it must SHARE — a constraint,
    not a free slot.  Substrate pins `roundtrip` to `flow` deliberately (weight and
    arrowhead carry the distinction instead of hue), and solving a pinned role as
    free would silently break a decision the consumer made on purpose.

    ⚑ EXHAUSTIVE, AND THAT IS A MEASUREMENT NOT A SHORTCUT.  With 7 members and at
    most 7 free roles the search is at most 7! = 5040 assignments; the palette
    solver needs restarts because it searches a generated candidate space orders of
    magnitude larger.  Here the optimum is FOUND, not approached, so the result
    carries no seed and no restart budget — and `solved_exhaustively` says so, so a
    reader never has to ask whether a better assignment was missed."""
    full = members or pool()
    members = eligible(ground, ground_floor, full)
    pinned = dict(pinned or {})

    free = [r for r in roles if r not in pinned]
    if not free:
        raise ValueError("every role is pinned; there is nothing to solve")
    if len(free) > len(members):
        if ground is not None and len(free) <= len(full):
            raise ValueError(
                f"{len(free)} free role(s) but only {len(members)} of {len(full)} "
                f"member(s) clear {ground_floor}:1 against the declared ground "
                f"{_hex(ground)} — eligible: {', '.join(sorted(members)) or '(none)'}. "
                f"The pool covers the roles for SEPARATION and not for LEGIBILITY on "
                f"this ground, and a best-effort assignment would place "
                f"{len(free) - len(members)} role(s) below the floor while still "
                f"scoring well. Drop a role, widen the pool, or declare no ground.")
        raise ValueError(
            f"{len(free)} free role(s) over {len(members)} palette member(s): the "
            f"pool cannot cover them, and an assignment reusing a colour would make "
            f"two roles indistinguishable rather than merely close")
    for role, target in pinned.items():
        if target not in roles:
            raise ValueError(f"{role!r} is pinned to {target!r}, which is not a role")
        if target in pinned:
            raise ValueError(f"{role!r} is pinned to {target!r}, which is itself pinned")

    names = sorted(members)
    floors = C.reference_floors()
    best = None
    for combo in itertools.permutations(names, len(free)):
        assign = {r: members[n] for r, n in zip(free, combo)}
        q, binding = worst_pair(assign, floors)
        if best is None or q > best[0]:
            best = (q, binding, dict(zip(free, combo)))

    q, binding, chosen = best
    out = dict(chosen)
    for role, target in pinned.items():
        out[role] = chosen[target]
    colours = {r: members[n] for r, n in out.items()}
    # ⚑ THE GROUND TRAVELS WITH THE ANSWER.  A consumer reading the artifact must be
    # able to tell WHICH objective was solved — an assignment optimal for mutual
    # distinctness and one optimal for distinctness-on-white are different answers
    # that look identical as a role->hex table.
    ground_contrast = None
    if ground is not None:
        ground_contrast = {r: round(C.wcag_ratio(c, tuple(ground)), 2)
                           for r, c in colours.items()}
    return {
        "roles": list(roles),
        "assignment": out,                       # role -> member NAME
        "colours": colours,
        "worst_q": q,
        "binding_pair": list(binding) if binding else None,
        "pinned": pinned,
        "floor_dE": C.reference_floor()[0],
        "ground": _hex(ground) if ground is not None else None,
        "ground_floor": ground_floor if ground is not None else None,
        "ground_contrast": ground_contrast,
        "solved_exhaustively": True,
    }


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(int(x) for x in rgb)


def as_json(solved, indent=2):
    """The assignment as JSON — parseable with no dependency on this module.

    ⚑ THAT INDEPENDENCE IS THE POINT OF THE ARTIFACT.  `cvd_gate` imports
    `colorspacious` and `numpy`, so a consumer without them cannot reach the
    measured palette AT ALL — substrate's `--palette` reports 'built-in fallback'
    rather than the measured source for exactly that reason.  A data file is
    readable where a live module is not."""
    return json.dumps({
        "roles": solved["roles"],
        "assignment": {r: _hex(c) for r, c in solved["colours"].items()},
        "member": solved["assignment"],
        "worst_q": round(solved["worst_q"], 4),
        "binding_pair": solved["binding_pair"],
        "pinned": solved["pinned"],
        "floor_dE": round(solved["floor_dE"], 2),
        "palette": "Okabe & Ito (2008) Color Universal Design, chromatic members",
        "metric": "worst_view_dE under Machado(2009) protan/deutan/tritan, "
                  "normalised by the Okabe-Ito reference floor",
        # ⚑ NULL HERE MEANS "NO GROUND WAS DECLARED", NOT "IT PASSES ON ANY GROUND".
        # Stated in the artifact because the difference is invisible in a role->hex
        # table and cost substrate three near-invisible edges.
        "ground": solved.get("ground"),
        "ground_floor": solved.get("ground_floor"),
        "ground_contrast": solved.get("ground_contrast"),
        "ground_note": ("solved for mutual distinctness ONLY — no ground was "
                        "declared, so these may be illegible as strokes on a "
                        "particular background; pass ground= to constrain that"
                        if solved.get("ground") is None else
                        f"every role also clears {solved['ground_floor']}:1 "
                        f"against {solved['ground']}"),
        "solved_exhaustively": solved["solved_exhaustively"],
    }, indent=indent, sort_keys=True) + "\n"


def as_dot(solved):
    """The assignment as graphviz, one named node per role carrying its colour.

    ⚑ `color`, NOT `edgecolor` — THE FIRST VERSION EMITTED AN ATTRIBUTE THAT DOES
    NOT EXIST.  graphviz has `color`, `fillcolor`, `fontcolor` and `bgcolor`; there
    is no `edgecolor`, so `read [edgecolor="#0072b2"]` parses as a well-formed
    graph and renders nothing — a valid file that is silently wrong, which is this
    repo's standing failure mode and the reason `check_role_theme.py` renders the
    emitted file rather than only parsing it.

    ⚑ AND IT CARRIES ITS OWN PROVENANCE AS COMMENTS, because a `.dot` that is only
    hexes is the bag-of-hexes the ask refuses.  A reader of the emitted file can see
    which metric chose the assignment, what the worst pair scored, and that the
    search was exhaustive rather than sampled."""
    lines = [
        "// role -> colour, SOLVED rather than listed.",
        "// palette: Okabe & Ito (2008), chromatic members.",
        "// metric:  worst_view_dE under Machado(2009) protan/deutan/tritan,",
        "//          normalised by the Okabe-Ito reference floor "
        f"(dE {solved['floor_dE']:.1f}).",
        f"// worst pair: q={solved['worst_q']:.3f}"
        + (f" at {solved['binding_pair'][0]}~{solved['binding_pair'][1]}"
           if solved["binding_pair"] else "")
        + "  (>= 1.0 clears the gate)",
        "// exhaustive over the pool: the optimum is FOUND, not approached.",
    ]
    # ⚑ THE GROUND MUST BE IN THE .dot TOO, NOT ONLY THE JSON.  A reader opening
    # this file alone cannot otherwise tell WHICH objective it answers, and the two
    # variants are byte-different files that look interchangeable — the same
    # absent-vs-empty confusion the null `ground` note exists to prevent.
    if solved.get("ground"):
        lines.append(f"// ground: every role also clears "
                     f"{solved['ground_floor']}:1 against {solved['ground']}, so "
                     f"these are legible AS STROKES on it.")
        if solved.get("ground_contrast"):
            worst = min(solved["ground_contrast"].items(), key=lambda kv: kv[1])
            lines.append(f"//         tightest: {worst[0]} at {worst[1]}:1.")
    else:
        lines.append("// ground: NONE DECLARED — solved for mutual distinctness "
                     "only. These may be")
        lines.append("//         illegible as strokes on a particular background; "
                     "see role-theme-on-white.dot.")
    if solved["pinned"]:
        for role, target in sorted(solved["pinned"].items()):
            lines.append(f"// {role} is PINNED to {target} — a declared constraint, "
                         f"not a free slot.")
    lines += ["", "graph role_theme {"]
    for role in solved["roles"]:
        member = solved["assignment"][role]
        colour = _hex(solved["colours"][role])
        lines.append(f'  {role} [color="{colour}"]  // {member}')
    lines.append("}")
    return "\n".join(lines) + "\n"


def _selftest():
    """Prove the solve is a solve, and that it can be shown wrong."""
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    p = pool()
    check("the pool is the published seven", len(p), 7)

    roles = ["read", "write", "pywrite", "flow"]
    s = solve_roles(roles)
    check("every role is assigned", sorted(s["assignment"]), sorted(roles))
    check("the assignment clears the floor", s["worst_q"] >= 1.0, True)
    check("no two roles share a colour",
          len({tuple(c) for c in s["colours"].values()}), len(roles))

    # ⚑ THE SOLVE MUST BEAT AN ARBITRARY ADMISSIBLE ASSIGNMENT, or it is decoration.
    # substrate's live one is the honest comparison: it clears, and it is not best.
    live = {"read": p["blue"], "write": p["bluegreen"],
            "pywrite": p["purple"], "flow": p["vermillion"]}
    lq, _ = worst_pair(live)
    check("substrate's live assignment clears", lq >= 1.0, True)
    check("the solve strictly beats it", s["worst_q"] > lq, True)

    # ⚑ AND NO ASSIGNMENT MAY BEAT THE SOLVED ONE — exhaustive means exhaustive.
    floors = C.reference_floors()
    names = sorted(p)
    better = [c for c in itertools.permutations(names, len(roles))
              if worst_pair({r: p[n] for r, n in zip(roles, c)}, floors)[0]
              > s["worst_q"] + 1e-12]
    check("nothing in the pool beats the solved assignment", better, [])

    # pinning is a constraint, and it must hold
    sp = solve_roles(["read", "write", "flow", "roundtrip"],
                     pinned={"roundtrip": "flow"})
    check("a pinned role shares its target's colour",
          sp["colours"]["roundtrip"], sp["colours"]["flow"])
    check("a pinned role still appears in the assignment",
          "roundtrip" in sp["assignment"], True)

    # refusals, each for a stated reason
    for label, args, kwargs in (
            ("more free roles than members", (["a"] * 8,), {}),
            ("a role pinned to a non-role", (["a", "b"],), {"pinned": {"b": "zz"}}),
            ("a role pinned to a pinned role",
             (["a", "b", "c"],), {"pinned": {"b": "c", "c": "b"}}),
    ):
        try:
            solve_roles(*args, **kwargs)
            check(f"refuses {label}", "passed", "raised")
        except ValueError:
            check(f"refuses {label}", "raised", "raised")

    # ⚑ THE GROUND CONSTRAINT, AND THE REFUSAL THAT MATTERS MOST.
    # Only 4 of 7 members clear 3:1 on white (blue, bluegreen, purple, vermillion),
    # so substrate's SIX roles are INFEASIBLE and must refuse rather than place
    # three roles below the floor with a healthy-looking q.
    WHITE = (255, 255, 255)
    el = eligible(WHITE, 3.0)
    check("4 of 7 members clear 3:1 on white", len(el), 4)
    check("no ground means every member is eligible", len(eligible(None)), 7)
    try:
        solve_roles(["read", "write", "pywrite", "flow", "roundtrip", "returns"],
                    ground=WHITE)
        check("six roles on white REFUSE", "passed", "raised")
    except ValueError as e:
        check("six roles on white REFUSE", "raised", "raised")
        check("...and the refusal names the eligible set", "eligible:" in str(e), True)
        check("...and distinguishes separation from legibility",
              "LEGIBILITY" in str(e), True)

    # four roles on white IS feasible, and every one must clear the ground floor
    g4 = solve_roles(["read", "write", "pywrite", "flow"], ground=WHITE)
    check("four roles on white solve", len(g4["assignment"]), 4)
    check("every role clears the ground floor",
          all(v >= 3.0 for v in g4["ground_contrast"].values()), True)
    check("the ground travels with the answer", g4["ground"], "#ffffff")
    # ⚑ AND THE UNGROUNDED SOLVE MUST *FAIL* THAT SAME TEST, or the constraint is
    # decoration — this is the exact defect substrate measured.
    u4 = solve_roles(["read", "write", "pywrite", "flow"])
    ung = {r: C.wcag_ratio(c, WHITE) for r, c in u4["colours"].items()}
    check("the ungrounded solve does NOT clear white",
          any(v < 3.0 for v in ung.values()), True)
    check("an ungrounded answer says so rather than implying safety",
          json.loads(as_json(u4))["ground"], None)

    # the emitted forms must be parseable without this module
    doc = json.loads(as_json(s))
    check("the JSON round-trips", sorted(doc["assignment"]), sorted(roles))
    check("the JSON carries its roles", doc["roles"], roles)
    check("the JSON states exhaustiveness", doc["solved_exhaustively"], True)
    dot = as_dot(s)
    check("the dot names every role", all(r in dot for r in roles), True)
    check("the dot carries its metric", "Machado" in dot, True)

    print("role_theme selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        raise SystemExit(0 if _selftest() else 1)
    s = solve_roles(["read", "write", "pywrite", "flow", "roundtrip"],
                    pinned={"roundtrip": "flow"})
    print(as_dot(s))
    print(as_json(s))
