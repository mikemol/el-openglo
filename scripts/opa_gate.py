#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""opa_gate.py — a check MEASURES (--json); a rego policy DECIDES; this joins them.

⚑ WHY (operator, 2026-09-22): "OPA and Rego is a standardized specification
format that's machine-parseable and machine-actionable. Our chk() arms, as
they are, are following a pattern I've seen overwhelm LLMs with cognitive
load." A check's Python shrinks to the measurement — a JSON document of what
it saw, SKIPs as `withheld` facts — and the REQUIREMENT lives in
policy/<name>.rego as `deny` / `withheld` sets, with its refusing and admitting
cases in policy/<name>_test.rego under `opa test`. The verdict is the set, never
a boolean: an empty population is a deny (the D0 guard), and could-not-measure
is kept apart from measured-defect.

    scripts/opa_gate.py <name>           # run scripts/check_<name>.py --json | opa eval data.el.<name>
                                         # exit 0 admitted / 1 denied / 3 withheld only
    scripts/opa_gate.py serial LOG       # OPERANDs after the name go to the measurement's --json
                                         # (MEASURERS maps a name to a non-check_ reader)
    scripts/opa_gate.py serial LOG --expect denied:S0
                                         # W75: the NEGATIVE claim — 0 only when the policy
                                         # decided and denied with exactly those rule ids;
                                         # admitted / other rule / crashed reader -> 1;
                                         # opa or the fixture absent -> 3 (see expect_gate)
    scripts/opa_gate.py --list           # every policy and whether its check has --json
    scripts/opa_gate.py --test           # opa test policy/ (every rule's refuse/admit pair)
    scripts/opa_gate.py --census [--cpu] # W50: which warrants cite opa_gate vs a bare check_*.py
                                         # (n of m decided in rego); --cpu times each Python one
    scripts/opa_gate.py --denies         # W75: which gated policies carry an --expect warrant
                                         # (the gate shown to FAIL end to end), n of m
    scripts/opa_gate.py --selftest

SKIP (exit 0, printed) when opa is absent — a fact about the host. Weakness: the
join is by NAME (check_<name>.py ↔ policy/<name>.rego ↔ package el.<name>); a
policy whose package does not match its file name evaluates to nothing, which
`--selftest` checks for every policy present.
"""

import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLICY = os.path.join(ROOT, "policy")
# ⚑ A SPEC'S CASE DATA SITS BESIDE IT (mikemol-pytestspec: `<spec>.cases.json`, W211) AND IS A JSON LIST, which
# opa refuses to load as a data document ("document must be of type object"): every opa call over the policy
# directory ignores it. The cases are pytest's input, never opa data.
IGNORE_CASES = ["--ignore", "*.cases.json"]
OPA = shutil.which("opa")

# ⚑ `opa test` HAS A 5 s WALL-CLOCK TIMEOUT PER TEST BY DEFAULT, AND THAT WAS THE @REGO FLAKE (W454,
# 2026-10-10). policy/cursors_test.rego's 35 tests cost ~1.3 s each ALONE; beside the gate's other
# checks (and 8 parallel copies of this one, scripts/flake_hunt.py --key REGO -j 8: 2 of 16 runs)
# a test crossed 5 s and failed `eval_cancel_error: context deadline exceeded`, and the replay
# passed because nothing else was running. A wall-clock verdict is a load verdict. The timeout here
# bounds a WEDGED test, never a slow one (operator 2026-09-24: "I hate wallclock-sensitive things"),
# so it is generous; the test's own cost is W454's follow-up (the cursors fixtures).
OPA_TEST_TIMEOUT = "300s"

# ⚑ A MEASUREMENT'S TIMEOUT IS A WEDGE BOUND TOO, NOT A VERDICT (W454's lesson, again: the 600 s here killed
# the closure witness stage, whose measurement is minutes of CPU that wall-clock load stretched past it,
# 2026-10-11, and the commit was refused for load). Seconds of wall time are load; two hours is a hang.
MEASURE_TIMEOUT = 7200


def policies():
    """[name] for every policy/<name>.rego that is not a _test."""
    return sorted(
        f[:-5]
        for f in os.listdir(POLICY)
        if f.endswith(".rego") and not f.endswith("_test.rego")
    )


# A policy whose measurement is not check_<name>.py. read_serial.py is a READER of
# an artifact the tree does not hold (a guest's serial log), so it takes the log as
# an operand: `opa_gate.py serial LOG` runs `read_serial.py --json LOG`.
MEASURERS = {"serial": "read_serial.py"}


def measurer(name):
    return os.path.join(ROOT, "scripts", MEASURERS.get(name, f"check_{name}.py"))


def measure(name, operands=(), script=None):
    """The check's --json document (a dict), run under this interpreter. `operands`
    (paths, resolved against the repo root) are passed after --json. `script`
    overrides the measurer (the --expect selftest's raising/garbage fixtures)."""
    script = script or measurer(name)
    r = subprocess.run(
        [sys.executable, script, "--json", *operands],
        capture_output=True,
        text=True,
        cwd=ROOT,
        timeout=MEASURE_TIMEOUT,
        check=False,
    )
    if r.returncode == 2:
        raise UsageRefusal(
            f"{os.path.basename(script)} refused its arguments (exit 2): "
            f"{r.stderr.strip()[-300:]}"
        )
    if r.returncode != 0:
        raise RuntimeError(
            f"{os.path.basename(script)} --json exited {r.returncode}: {r.stderr[-300:]}"
        )
    return json.loads(r.stdout)


class UsageRefusal(RuntimeError):
    """The measurer exited 2 (usage): the operands are wrong, which is not a crash.
    gate() reports it and exits 2; expect_gate still counts it a failed claim."""


def value(name, doc):
    """The whole of data.el.<name> over the measurement — every rule the policy
    defines, for a check whose listing mode shows what the POLICY derived (e.g.
    check_mark --files reads `offending`) rather than re-deriving it in Python."""
    r = subprocess.run(
        [
            OPA,
            "eval",
            "-f",
            "json",
            "-I",
            *IGNORE_CASES,
            "-d",
            POLICY,
            f"data.el.{name}",
        ],
        input=json.dumps(doc),
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(f"opa eval exited {r.returncode}: {r.stderr[-300:]}")
    res = json.loads(r.stdout)["result"]
    if not res:
        raise RuntimeError(
            f"data.el.{name} is undefined — no package el.{name} in policy/"
        )
    return res[0]["expressions"][0]["value"]


def evaluate(name, doc):
    """{'deny': [...], 'withheld': [...]} from opa over the measurement."""
    v = value(name, doc)
    # `admitted` is OPTIONAL: a policy that judges a population case by case
    # declares what it admitted, so a withheld case beside admitted ones is a
    # SKIP (a fact about the host) rather than "nothing was judged" (s131)
    return {
        "deny": sorted(v.get("deny", [])),
        "withheld": sorted(v.get("withheld", [])),
        "admitted": sorted(v["admitted"]) if "admitted" in v else None,
    }


def verdict(sets):
    """0 admitted, 1 denied, 3 withheld-only. A policy that declares `admitted` and
    admitted SOMETHING is 0 even with withheld cases — those are counted and
    printed as SKIPs; a policy without `admitted`, or one that admitted nothing,
    is 3 when anything is withheld: nothing was judged."""
    if sets["deny"]:
        return 1
    if sets["withheld"] and not sets.get("admitted"):
        return 3
    return 0


def census():
    """The W50 migration population, from warrants.bib's `check` fields (read by
    check_tree_writes.claims — bibstruct, one reader). {'gate': [(key, name)],
    'direct': [(key, script, args)]}: a claim citing `tool:opa_gate.py <name>` is
    migrated; one citing `tool:check_*.py` bare (no flags) decides in Python and is
    the population still to migrate. A `--selftest` citation is a SEES claim — the
    measurement's own can-it-see test, which stays Python by the rule — and is not
    counted in either. Weakness: a claim citing some other tool is outside both."""
    import check_tree_writes

    out = {"gate": [], "direct": []}
    for key, check in check_tree_writes.claims(ROOT):
        kind, _, rest = check.partition(":")
        argv_ = rest.split()
        if kind != "tool" or not argv_:
            continue
        if (
            argv_[0] == "opa_gate.py"
            and len(argv_) > 1
            and not argv_[1].startswith("--")
        ):
            out["gate"].append((key, argv_[1]))
        elif argv_[0].startswith("check_") and len(argv_) == 1:
            out["direct"].append((key, argv_[0], argv_[1:]))
    return out


def denies_census():
    """W75: per GATED policy, the warrants that claim it can FAIL end to end.

    `opa test` proves each RULE refuses its fixture; it never runs the measurement.
    A warrant citing `opa_gate.py <name> FIXTURE --expect denied:<RULE>` proves the
    whole path — measurement, policy, exit — reaches a denial on a known-bad input.
    {name: [keys of --expect warrants]} over every name some warrant gates on; a
    name with [] has no end-to-end negative claim. Weakness: a policy with no
    fixture operand (its measurement reads the tree, not a file) cannot take one
    this way; the census reports it all the same, as work, not as an exemption."""
    import check_tree_writes

    out = {}
    for key, check in check_tree_writes.claims(ROOT):
        kind, _, rest = check.partition(":")
        argv_ = rest.split()
        if (
            kind != "tool"
            or len(argv_) < 2
            or argv_[0] != "opa_gate.py"
            or argv_[1].startswith("--")
        ):
            continue
        out.setdefault(argv_[1], [])
        if any(a == "--expect" or a.startswith("--expect=") for a in argv_):
            out[argv_[1]].append(key)
    return out


def cpu_of(script):
    """(rc, user+sys CPU seconds) of one run of scripts/<script> — its own CPU, never
    wall (the box is shared and loaded)."""
    import resource

    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", script)],
        capture_output=True,
        cwd=ROOT,
        timeout=900,
        check=False,
    )
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return r.returncode, (after.ru_utime - before.ru_utime) + (
        after.ru_stime - before.ru_stime
    )


def main(argv):
    known = {
        "--list",
        "--test",
        "--specs",
        "--portable",
        "--selftest",
        "--census",
        "--cpu",
        "--denies",
    }
    rest, expect = list(argv[1:]), None
    # --expect takes a VALUE (`--expect denied:S0` or `--expect=denied:S0`); it is
    # lifted out before the flag/operand split so the value is not read as an operand
    for i, a in enumerate(rest):
        if a == "--expect" or a.startswith("--expect="):
            val = (
                a.partition("=")[2]
                if "=" in a
                else (rest[i + 1] if i + 1 < len(rest) else "")
            )
            del rest[i : i + (1 if "=" in a else 2)]
            expect = parse_expect(val)
            if expect is None:
                print(
                    f"opa_gate: --expect wants denied:<RULE>[,<RULE>...], got {val!r}",
                    file=sys.stderr,
                )
                return 2
            break
    args = [a for a in rest if a.startswith("--")]
    names = [a for a in rest if not a.startswith("--")]
    if expect is not None and (args or not names):
        print(
            "opa_gate: --expect qualifies `<name> [OPERAND...]` and nothing else",
            file=sys.stderr,
        )
        return 2
    if expect is not None:
        return expect_gate(names[0], names[1:], expect)
    for a in args:
        if a not in known:
            print(f"opa_gate: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--census" in args:
        c = census()
        for key, name in c["gate"]:
            print(f"  rego    @{key:20s} opa_gate.py {name}")
        scripts = sorted({s for _, s, _ in c["direct"]})
        for key, script, _ in c["direct"]:
            if "--cpu" in args:
                rc, cpu = cpu_of(script)
                print(f"  python  @{key:20s} {script:32s} rc={rc} cpu={cpu:.2f}s")
            else:
                print(f"  python  @{key:20s} {script}")
        n, m = len(c["gate"]), len(c["gate"]) + len(c["direct"])
        print(
            f"opa_gate census: {n} of {m} gate claims decided in rego; "
            f"{len(c['direct'])} claims ({len(scripts)} scripts) still decide in Python"
        )
        return 0 if m else 2
    if "--denies" in args:
        d = denies_census()
        for name in sorted(d):
            keys = d[name]
            print(
                f"  {'fails' if keys else 'NONE ':5s}  {name:22s} "
                + (
                    ", ".join(f"@{k}" for k in keys)
                    if keys
                    else "no end-to-end negative claim"
                )
            )
        n = sum(1 for k in d.values() if k)
        print(
            f"opa_gate denies: {n} of {len(d)} gated policies carry a claim that the gate "
            f"DENIES a known-bad fixture (W75)"
        )
        return 0 if d else 2
    if "--cpu" in args:
        print("opa_gate: --cpu only qualifies --census", file=sys.stderr)
        return 2
    if not OPA:
        print("opa_gate: SKIP — opa is not installed on this host", file=sys.stderr)
        return 0
    if "--list" in args:
        for n in policies():
            m = measurer(n)
            print(
                f"{n:24s} policy/{n}.rego  {os.path.basename(m)} {'--json' if os.path.isfile(m) else 'ABSENT'}"
            )
        return 0
    if "--specs" in args:
        return specs_gate()
    if "--portable" in args:
        return portable_report()
    if "--test" in args:
        r = subprocess.run(
            [OPA, "test", "--timeout", OPA_TEST_TIMEOUT, *IGNORE_CASES, POLICY],
            capture_output=True,
            text=True,
            check=False,
        )
        print(r.stdout.strip() or r.stderr.strip())
        return r.returncode
    if not names:
        print(
            "usage: opa_gate.py <name> [OPERAND...] | --list | --test | --selftest",
            file=sys.stderr,
        )
        return 2
    return gate(names[0], names[1:])


def _strings(node):
    """Every string term in an opa AST node (a parsed rule): the literals AND the reference segments, so
    `p.admitted` contributes "admitted". A structural walk of the parse, never a text search of the source."""
    out, stack = set(), [node]
    while stack:
        n = stack.pop()
        if isinstance(n, dict):
            if n.get("type") == "string":
                out.add(n.get("value"))
            stack.extend(n.values())
        elif isinstance(n, list):
            stack.extend(n)
    return out


def test_census(policy_dir=POLICY, opa=None):
    """{spec: (tests, admitted_tests)} for every `<spec>_test.rego`, read from `opa parse` (W558).

    A test is a rule named test_*; it is ADMITTED-ASSERTING when its parse mentions the `admitted` set, which a
    pytestspec case cannot express (a case judges the deny and withheld rule-id sets only), so the others are
    PORTABLE. A test file opa cannot parse maps to None: counted by the caller, never read as zero tests.
    WEAKNESS: a test that reaches `admitted` through a helper rule it defines is read as portable (the walk is
    per rule, not across rules); the mutation control of a ported spec is what would catch it."""
    opa = opa or OPA
    out = {}
    for fn in sorted(os.listdir(policy_dir)):
        if not fn.endswith("_test.rego"):
            continue
        r = subprocess.run(
            [opa, "parse", "--format", "json", os.path.join(policy_dir, fn)],
            capture_output=True,
            text=True,
            check=False,
        )
        if r.returncode != 0:
            out[fn.removesuffix("_test.rego")] = None
            continue
        rules = json.loads(r.stdout).get("rules", [])
        tests = [x for x in rules if x["head"].get("name", "").startswith("test_")]
        asserting = [x for x in tests if "admitted" in _strings(x)]
        out[fn.removesuffix("_test.rego")] = (len(tests), len(asserting))
    return out


def portable_report(policy_dir=POLICY, census=None):
    """Print, per spec, how many of its tests a pytestspec case could carry; the exit code (W558).

    One line per spec with tests, the most portable first (the order a sweep wants): tests, admitted-asserting,
    portable, and whether a cases file already exists. Then `n of m`: the portable tests of all tests, the specs
    already carrying cases of those with tests. 2 when no test file was read at all (a broken search, not a tree
    with nothing to port); a test file opa could not parse is listed as UNPARSED and fails the run (1)."""
    census = test_census(policy_dir) if census is None else census
    have = set(spec_cases(policy_dir)[0])
    rows, bad = [], []
    for spec, got in census.items():
        if got is None:
            bad.append(spec)
        elif got[0]:
            rows.append((spec, got[0], got[1], got[0] - got[1]))
    if not rows and not bad:
        print("opa_gate --portable: REFUSED — no test file was read", file=sys.stderr)
        return 2
    for spec, n, a, p in sorted(rows, key=lambda r: (-(r[3] / r[1]), -r[1], r[0])):
        mark = "cases" if os.path.join("policy", spec + ".rego") in have else "     "
        print(
            f"  {spec:24s} tests {n:3d}  admitted-asserting {a:3d}  portable {p:3d}  {mark}"
        )
    for spec in bad:
        print(f"  {spec:24s} UNPARSED: opa parse refused the test file")
    total = sum(n for _s, n, _a, _p in rows)
    port = sum(p for _s, _n, _a, p in rows)
    ported = sum(1 for s, *_ in rows if os.path.join("policy", s + ".rego") in have)
    print(
        f"opa_gate --portable: {port} of {total} tests portable over {len(rows)} spec(s); "
        f"{ported} of {len(rows)} already carry cases"
    )
    return 1 if bad else 0


def spec_cases(policy_dir=POLICY):
    """(specs, orphans): the specs that carry a pytestspec cases file, and the cases files with no spec.

    A spec is `policy/<name>.rego` with `policy/<name>.cases.json` beside it (mikemol-pytestspec, W211).
    Specs are returned as repo-relative paths (what pytest is handed); an orphan is a `<name>.cases.json` whose
    `<name>.rego` is gone, which pytest would never collect and nothing else would read: stale data that looks
    like coverage. WEAKNESS: it reads names, not the cases; whether a case is any good is the spec's mutation
    control, not this census."""
    specs, orphans = [], []
    for fn in sorted(os.listdir(policy_dir)):
        if not fn.endswith(".cases.json"):
            continue
        stem = fn.removesuffix(".cases.json")
        if os.path.isfile(os.path.join(policy_dir, stem + ".rego")):
            specs.append(os.path.join("policy", stem + ".rego"))
        else:
            orphans.append(os.path.join("policy", fn))
    return specs, orphans


def stored_closure(key="pytestspec", bzl=None):
    """The stored closure of a gate stage, read from closures.bzl with check_closure's own reader; None when
    closures.bzl cannot be read here (a tree that holds only some stage's closure) or holds no such key."""
    import check_closure as CC

    try:
        with open(bzl or os.path.join(ROOT, "closures.bzl"), encoding="utf-8") as fh:
            return CC.load_closures(fh.read()).get(key)
    except OSError:
        return None


def closure_lacks(specs, closure):
    """The cases files of `specs` that `closure` does not hold. ⚑ A cases file the stage closure lacks is
    SILENT: in bazel the stage's inputs are its closure, so it would run fewer specs than the tree has and
    pass (W558, found porting codomain). Run `check_closure.py --write pytestspec` after adding one."""
    wanted = [s.removesuffix(".rego") + ".cases.json" for s in specs]
    return [c for c in wanted if c not in closure]


def specs_gate(policy_dir=POLICY, run=None, closure="stored"):
    """Run pytest over every spec that has a cases file; the exit code (W557).

    0 when every case passed, pytest's own code when one did not, 1 on an orphan cases file, 2 when no spec has
    a cases file at all (an empty population is a broken search, never a green run). It prints `n of m`: the
    specs that have cases of the policies there are. `run` is the seam a selftest fakes (argv -> rc)."""
    specs, orphans = spec_cases(policy_dir)
    for o in orphans:
        print(f"opa_gate --specs: {o} has no spec beside it", file=sys.stderr)
    if orphans:
        return 1
    if not specs:
        print(
            "opa_gate --specs: REFUSED — no spec has a cases file; the population is empty",
            file=sys.stderr,
        )
        return 2
    held = stored_closure() if closure == "stored" else closure
    lacking = closure_lacks(specs, held) if held is not None else []
    for c in lacking:
        print(
            f"opa_gate --specs: {c} is not in the stored pytestspec closure; "
            "run check_closure.py --write pytestspec (bazel would run fewer specs and pass)",
            file=sys.stderr,
        )
    if lacking:
        return 1
    argv = [sys.executable, "-m", "pytest", *specs, "-q", "-p", "no:cacheprovider"]
    rc = run(argv) if run else subprocess.run(argv, cwd=ROOT, check=False).returncode
    print(
        f"opa_gate --specs: {len(specs)} of {len(policies())} policy spec(s) carry cases"
    )
    return rc


def gate(name, operands=()):
    """Measure, decide, print the verdict; the exit code. A migrated check's bare mode
    is exactly this call — it prints what the policy decided and decides nothing."""
    if not OPA:
        print(
            f"opa_gate: {name}: SKIP — opa is not installed on this host",
            file=sys.stderr,
        )
        return 0
    try:
        doc = measure(name, operands)
    except UsageRefusal as e:
        print(f"opa_gate: {name}: usage — {e}", file=sys.stderr)
        return 2
    sets = evaluate(name, doc)
    for m in sets["deny"]:
        print(f"opa_gate: DENY {m}", file=sys.stderr)
    for m in sets["withheld"]:
        print(f"opa_gate: WITHHELD {m}", file=sys.stderr)
    rc = verdict(sets)
    adm = (
        f", {len(sets['admitted'])} admitted"
        if sets.get("admitted") is not None
        else ""
    )
    print(
        f"opa_gate: {name}: {'admitted' if rc == 0 else 'DENIED' if rc == 1 else 'withheld'} — "
        f"{len(sets['deny'])} deny, {len(sets['withheld'])} withheld{adm}"
    )
    return rc


RULE_ID = re.compile(r"[A-Z][A-Za-z0-9]*")


def parse_expect(val):
    """`denied:S0[,S1...]` -> frozenset of rule ids; None when malformed. Only
    `denied` is a kind: an expected ADMISSION is the bare gate's exit 0 already."""
    kind, _, ids = val.partition(":")
    rules = frozenset(x for x in ids.split(",") if x)
    if kind != "denied" or not rules or not all(RULE_ID.fullmatch(x) for x in rules):
        return None
    return rules


def rule_of(msg):
    """The rule id a deny message carries — its `S0:` prefix — or None."""
    head = msg.partition(":")[0]
    return head if ":" in msg and RULE_ID.fullmatch(head) else None


def expect_gate(name, operands, rules, script=None, opa=None):
    """W75 — the claim that a gate DENIES a negative fixture, with the TYPED denial.
    paperkit keeps one exit meaning (0 pass / 3 could-not-run / else fail), so the
    inversion lives here, and it must not pass on anything but the denial asked for:

      0  the measurement ran, the policy DECIDED, it denied, and the set of rule ids
         carried by its deny messages is EXACTLY `rules`. ⚑ Decided: exactly, not
         superset — an extra rule firing means the reader measured something other
         than the fixture it was pointed at, which is the mutation to catch. A deny
         message with no rule-id prefix counts as an unexpected rule.
      1  admitted; withheld-only (it did not decide); a different rule; the
         measurement crashed, failed to import, or printed unparseable JSON; opa
         eval failed or the package is undefined. A broken reader is a FAILED claim —
         were it 3 or 0, every mutation that breaks the reader would grade vacuous.
      3  could not run: opa is absent, or an operand (the fixture) does not exist.

    Weakness: operands are taken to be paths (true of every current measurer that
    takes one); a non-path operand would read as an absent fixture and exit 3.
    `script` / `opa` are the selftest's injection points."""
    want = ",".join(sorted(rules))
    opa = OPA if opa is None else opa
    if not opa:
        print(
            f"opa_gate: {name}: COULD NOT RUN — opa is not installed on this host",
            file=sys.stderr,
        )
        return 3
    missing = [op for op in operands if not os.path.exists(op)]
    if missing:
        print(
            f"opa_gate: {name}: COULD NOT RUN — operand(s) absent: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 3
    try:
        sets = evaluate(name, measure(name, operands, script))
    except Exception as e:  # noqa: BLE001 — every crash class is the SAME verdict: fail
        print(
            f"opa_gate: {name}: FAIL — expected a {want} denial, the gate did not decide: "
            f"{type(e).__name__}: {e}",
            file=sys.stderr,
        )
        return 1
    for m in sets["deny"]:
        print(f"opa_gate: DENY {m}", file=sys.stderr)
    for m in sets["withheld"]:
        print(f"opa_gate: WITHHELD {m}", file=sys.stderr)
    if not sets["deny"]:
        got = "withheld" if verdict(sets) == 3 else "admitted"
        print(f"opa_gate: {name}: FAIL — expected a {want} denial, got {got}")
        return 1
    fired = {rule_of(m) or "<no rule id>" for m in sets["deny"]}
    if fired != set(rules):
        print(
            f"opa_gate: {name}: FAIL — expected a {want} denial, got {','.join(sorted(fired))} "
            f"({len(sets['deny'])} deny)"
        )
        return 1
    print(
        f"opa_gate: {name}: expected denial — {want} fired ({len(sets['deny'])} deny, "
        f"{len(sets['withheld'])} withheld)"
    )
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    if not OPA:
        print("  SKIP — opa absent")
        print("opa_gate selftest: SKIP")
        return True
    ps = policies()
    chk("at least one policy", len(ps) > 0, True)
    for n in ps:
        # every policy answers to its name and ADMITS NOTHING on an empty input:
        # a measurement that measured nothing is denied (D0) or withheld, never
        # admitted (verdict 0)
        sets = evaluate(n, {})
        chk(f"{n}: an empty measurement is not admitted", verdict(sets) != 0, True)
        chk(f"{n}: a check with --json exists", os.path.isfile(measurer(n)), True)
    chk("verdict maps deny to 1", verdict({"deny": ["x"], "withheld": []}), 1)
    chk("verdict maps withheld-only to 3", verdict({"deny": [], "withheld": ["x"]}), 3)
    chk("verdict maps empty sets to 0", verdict({"deny": [], "withheld": []}), 0)
    chk(
        "a withheld case beside admitted ones is a SKIP (0)",
        verdict({"deny": [], "withheld": ["x"], "admitted": ["a"]}),
        0,
    )
    chk(
        "a withheld case with nothing admitted is 3",
        verdict({"deny": [], "withheld": ["x"], "admitted": []}),
        3,
    )
    chk(
        "a deny outranks admitted",
        verdict({"deny": ["d"], "withheld": [], "admitted": ["a"]}),
        1,
    )
    r = subprocess.run(
        [OPA, "test", "--timeout", OPA_TEST_TIMEOUT, *IGNORE_CASES, POLICY],
        capture_output=True,
        text=True,
        check=False,
    )
    chk("opa test policy/ passes", r.returncode, 0)
    # W75 --expect: one arm per outcome, over the real serial reader and fixtures
    import tempfile

    fx = os.path.join("catalog", "fixtures", "serial")
    noise, clean = os.path.join(fx, "noise-only.log"), os.path.join(fx, "clean.log")
    s0 = parse_expect("denied:S0")
    chk("--expect parses denied:S0", s0, frozenset({"S0"}))
    chk(
        "--expect refuses admitted:S0 / denied: / denied:s0",
        [parse_expect(v) for v in ("admitted:S0", "denied:", "denied:s0")],
        [None, None, None],
    )
    chk(
        "--expect: the expected denial passes (0)",
        expect_gate("serial", [noise], s0),
        0,
    )
    chk("--expect: admitted fails (1)", expect_gate("serial", [clean], s0), 1)
    chk(
        "--expect: a different rule fails (1)",
        expect_gate("serial", [noise], parse_expect("denied:S1")),
        1,
    )
    chk(
        "--expect: a superset expectation fails (1)",
        expect_gate("serial", [noise], parse_expect("denied:S0,S1")),
        1,
    )
    with tempfile.TemporaryDirectory() as td:
        raising = os.path.join(td, "raising.py")
        garbage = os.path.join(td, "garbage.py")
        with open(raising, "w") as f:
            f.write("raise ImportError('fixture: the reader does not import')\n")
        with open(garbage, "w") as f:
            f.write("print('this is not json')\n")
        chk(
            "--expect: a raising measurer FAILS (1), never 0",
            expect_gate("serial", [noise], s0, script=raising),
            1,
        )
        chk(
            "--expect: unparseable JSON FAILS (1)",
            expect_gate("serial", [noise], s0, script=garbage),
            1,
        )
        try:
            measure("serial", [], raising)
            crash = "no exception"
        except UsageRefusal:
            crash = "UsageRefusal"
        except RuntimeError:
            crash = "RuntimeError"
        chk(
            "a crashing measurer (exit 1) is a RuntimeError, not a usage refusal",
            crash,
            "RuntimeError",
        )
    chk(
        "--expect: an absent fixture could not run (3)",
        expect_gate("serial", [os.path.join(fx, "absent.log")], s0),
        3,
    )
    chk(
        "--expect: opa absent could not run (3)",
        expect_gate("serial", [noise], s0, opa=""),
        3,
    )
    chk(
        "--expect: an undefined package FAILS (1)",
        expect_gate("no_such_policy", [noise], s0, script=measurer("serial")),
        1,
    )
    # W182: a measurer's usage refusal (exit 2) is a usage refusal, not a traceback
    chk("gate: serial with no LOG operand exits 2", gate("serial", []), 2)
    # W75 --denies: the census SEES a negative claim where one exists, and its absence
    d = denies_census()
    chk(
        "--denies sees SERIAL-DENIES on serial",
        "SERIAL-DENIES" in d.get("serial", []),
        True,
    )
    chk(
        "--denies reports a gated policy with no negative claim as [] (not absent)",
        any(v == [] for v in d.values()),
        True,
    )
    # W557 --specs: the finder SEES a spec with cases, one without, and an orphan; the gate refuses an
    # empty population and an orphan, and returns the runner's own code otherwise
    import contextlib
    import io
    import tempfile

    a_spec = os.path.join("policy", "a.rego")
    gone = os.path.join("policy", "gone.cases.json")
    quiet = io.StringIO()
    with tempfile.TemporaryDirectory() as pd:
        for fn in ("a.rego", "a.cases.json", "b.rego", "gone.cases.json"):
            with open(os.path.join(pd, fn), "w", encoding="utf-8") as fh:
                fh.write("[]")
        chk(
            "--specs: a spec with cases is found, one without is not, a cases file with no spec is an orphan",
            spec_cases(pd),
            ([a_spec], [gone]),
        )
        with contextlib.redirect_stderr(quiet):
            orphaned = specs_gate(pd, run=lambda argv: 0)
        chk("--specs: an orphan cases file fails the gate (1)", orphaned, 1)
        os.remove(os.path.join(pd, "gone.cases.json"))
        ran = []
        with contextlib.redirect_stdout(quiet):
            rc = specs_gate(pd, run=lambda argv: ran.append(argv) or 5, closure=None)
        chk(
            "--specs: a clean population hands pytest the spec and returns the runner's own code",
            (rc, a_spec in ran[0]),
            (5, True),
        )
        # W558 guard: a cases file the stored stage closure lacks is a refusal that names the fix
        said = io.StringIO()
        with contextlib.redirect_stderr(said):
            lacked = specs_gate(pd, run=lambda argv: 0, closure=[])
        chk(
            "--specs: a cases file the stage closure lacks fails the gate (1) and names the fix",
            (lacked, "check_closure.py --write pytestspec" in said.getvalue()),
            (1, True),
        )
        with contextlib.redirect_stdout(quiet):
            held = specs_gate(pd, run=lambda argv: 0, closure=["policy/a.cases.json"])
        chk("--specs: a closure that holds the cases file runs the specs", held, 0)
        chk(
            "closure_lacks: only the cases files the closure does not hold",
            closure_lacks(["policy/a.rego", "policy/b.rego"], ["policy/a.cases.json"]),
            ["policy/b.cases.json"],
        )
        os.remove(os.path.join(pd, "a.cases.json"))
        with contextlib.redirect_stderr(quiet):
            empty = specs_gate(pd, run=lambda argv: 0)
        chk(
            "--specs: no spec with cases at all is REFUSED (2), never a green run",
            empty,
            2,
        )
    # W558 --portable: a test that mentions the admitted set is told from one that does not, by the parse
    with tempfile.TemporaryDirectory() as pd:
        with open(os.path.join(pd, "x_test.rego"), "w", encoding="utf-8") as fh:
            fh.write(
                "package el.x_test\n\nimport rego.v1\n\n"
                "test_denies if count(data.el.x.deny) == 1\n\n"
                "test_withheld if count(data.el.x.withheld) == 0\n\n"
                'test_admits if data.el.x.admitted == {"a"}\n\n'
                "helper := 1\n"
            )
        with open(os.path.join(pd, "bad_test.rego"), "w", encoding="utf-8") as fh:
            fh.write("package el.bad_test\n\ntest_x if {\n")
        census = test_census(pd)
        chk(
            "--portable: three tests, one of them asserting the admitted set; a non-test rule is not counted",
            census.get("x"),
            (3, 1),
        )
        chk(
            "--portable: a test file opa cannot parse is None, never zero tests",
            census.get("bad", "absent"),
            None,
        )
        with contextlib.redirect_stdout(quiet), contextlib.redirect_stderr(quiet):
            unparsed = portable_report(pd, census)
            nothing = portable_report(pd, {})
            clean = portable_report(pd, {"x": (3, 1)})
        chk(
            "--portable: an unparsed test file fails the report (1), an empty census is refused (2), a clean one is 0",
            (unparsed, nothing, clean),
            (1, 2, 0),
        )
    print("opa_gate selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
