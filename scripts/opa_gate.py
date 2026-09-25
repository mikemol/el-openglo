#!/usr/bin/env python3
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
OPA = shutil.which("opa")


def policies():
    """[name] for every policy/<name>.rego that is not a _test."""
    return sorted(f[:-5] for f in os.listdir(POLICY) if f.endswith(".rego") and not f.endswith("_test.rego"))


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
    r = subprocess.run([sys.executable, script, "--json", *operands],
                       capture_output=True, text=True, cwd=ROOT, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"{os.path.basename(script)} --json exited {r.returncode}: {r.stderr[-300:]}")
    return json.loads(r.stdout)


def value(name, doc):
    """The whole of data.el.<name> over the measurement — every rule the policy
    defines, for a check whose listing mode shows what the POLICY derived (e.g.
    check_mark --files reads `offending`) rather than re-deriving it in Python."""
    r = subprocess.run([OPA, "eval", "-f", "json", "-I", "-d", POLICY, f"data.el.{name}"],
                       input=json.dumps(doc), capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"opa eval exited {r.returncode}: {r.stderr[-300:]}")
    res = json.loads(r.stdout)["result"]
    if not res:
        raise RuntimeError(f"data.el.{name} is undefined — no package el.{name} in policy/")
    return res[0]["expressions"][0]["value"]


def evaluate(name, doc):
    """{'deny': [...], 'withheld': [...]} from opa over the measurement."""
    v = value(name, doc)
    # `admitted` is OPTIONAL: a policy that judges a population case by case
    # declares what it admitted, so a withheld case beside admitted ones is a
    # SKIP (a fact about the host) rather than "nothing was judged" (s131)
    return {"deny": sorted(v.get("deny", [])), "withheld": sorted(v.get("withheld", [])),
            "admitted": sorted(v["admitted"]) if "admitted" in v else None}


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
        if argv_[0] == "opa_gate.py" and len(argv_) > 1 and not argv_[1].startswith("--"):
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
        if kind != "tool" or len(argv_) < 2 or argv_[0] != "opa_gate.py" or argv_[1].startswith("--"):
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
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", script)],
                       capture_output=True, cwd=ROOT, timeout=900)
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    return r.returncode, (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)


def main(argv):
    known = {"--list", "--test", "--selftest", "--census", "--cpu", "--denies"}
    rest, expect = list(argv[1:]), None
    # --expect takes a VALUE (`--expect denied:S0` or `--expect=denied:S0`); it is
    # lifted out before the flag/operand split so the value is not read as an operand
    for i, a in enumerate(rest):
        if a == "--expect" or a.startswith("--expect="):
            val = a.partition("=")[2] if "=" in a else (rest[i + 1] if i + 1 < len(rest) else "")
            del rest[i:i + (1 if "=" in a else 2)]
            expect = parse_expect(val)
            if expect is None:
                print(f"opa_gate: --expect wants denied:<RULE>[,<RULE>...], got {val!r}", file=sys.stderr)
                return 2
            break
    args = [a for a in rest if a.startswith("--")]
    names = [a for a in rest if not a.startswith("--")]
    if expect is not None and (args or not names):
        print("opa_gate: --expect qualifies `<name> [OPERAND...]` and nothing else", file=sys.stderr)
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
        print(f"opa_gate census: {n} of {m} gate claims decided in rego; "
              f"{len(c['direct'])} claims ({len(scripts)} scripts) still decide in Python")
        return 0 if m else 2
    if "--denies" in args:
        d = denies_census()
        for name in sorted(d):
            keys = d[name]
            print(f"  {'fails' if keys else 'NONE ':5s}  {name:22s} " +
                  (", ".join(f"@{k}" for k in keys) if keys else "no end-to-end negative claim"))
        n = sum(1 for k in d.values() if k)
        print(f"opa_gate denies: {n} of {len(d)} gated policies carry a claim that the gate "
              f"DENIES a known-bad fixture (W75)")
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
            print(f"{n:24s} policy/{n}.rego  {os.path.basename(m)} {'--json' if os.path.isfile(m) else 'ABSENT'}")
        return 0
    if "--test" in args:
        r = subprocess.run([OPA, "test", POLICY], capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip())
        return r.returncode
    if not names:
        print("usage: opa_gate.py <name> [OPERAND...] | --list | --test | --selftest", file=sys.stderr)
        return 2
    return gate(names[0], names[1:])


def gate(name, operands=()):
    """Measure, decide, print the verdict; the exit code. A migrated check's bare mode
    is exactly this call — it prints what the policy decided and decides nothing."""
    if not OPA:
        print(f"opa_gate: {name}: SKIP — opa is not installed on this host", file=sys.stderr)
        return 0
    sets = evaluate(name, measure(name, operands))
    for m in sets["deny"]:
        print(f"opa_gate: DENY {m}", file=sys.stderr)
    for m in sets["withheld"]:
        print(f"opa_gate: WITHHELD {m}", file=sys.stderr)
    rc = verdict(sets)
    adm = f", {len(sets['admitted'])} admitted" if sets.get("admitted") is not None else ""
    print(f"opa_gate: {name}: {'admitted' if rc == 0 else 'DENIED' if rc == 1 else 'withheld'} — "
          f"{len(sets['deny'])} deny, {len(sets['withheld'])} withheld{adm}")
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
        print(f"opa_gate: {name}: COULD NOT RUN — opa is not installed on this host", file=sys.stderr)
        return 3
    missing = [op for op in operands if not os.path.exists(op)]
    if missing:
        print(f"opa_gate: {name}: COULD NOT RUN — operand(s) absent: {', '.join(missing)}", file=sys.stderr)
        return 3
    try:
        sets = evaluate(name, measure(name, operands, script))
    except Exception as e:  # noqa: BLE001 — every crash class is the SAME verdict: fail
        print(f"opa_gate: {name}: FAIL — expected a {want} denial, the gate did not decide: "
              f"{type(e).__name__}: {e}", file=sys.stderr)
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
        print(f"opa_gate: {name}: FAIL — expected a {want} denial, got {','.join(sorted(fired))} "
              f"({len(sets['deny'])} deny)")
        return 1
    print(f"opa_gate: {name}: expected denial — {want} fired ({len(sets['deny'])} deny, "
          f"{len(sets['withheld'])} withheld)")
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
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
    chk("a withheld case beside admitted ones is a SKIP (0)", verdict({"deny": [], "withheld": ["x"], "admitted": ["a"]}), 0)
    chk("a withheld case with nothing admitted is 3", verdict({"deny": [], "withheld": ["x"], "admitted": []}), 3)
    chk("a deny outranks admitted", verdict({"deny": ["d"], "withheld": [], "admitted": ["a"]}), 1)
    r = subprocess.run([OPA, "test", POLICY], capture_output=True, text=True)
    chk("opa test policy/ passes", r.returncode, 0)
    # W75 --expect: one arm per outcome, over the real serial reader and fixtures
    import tempfile
    fx = os.path.join("catalog", "fixtures", "serial")
    noise, clean = os.path.join(fx, "noise-only.log"), os.path.join(fx, "clean.log")
    s0 = parse_expect("denied:S0")
    chk("--expect parses denied:S0", s0, frozenset({"S0"}))
    chk("--expect refuses admitted:S0 / denied: / denied:s0",
        [parse_expect(v) for v in ("admitted:S0", "denied:", "denied:s0")], [None, None, None])
    chk("--expect: the expected denial passes (0)", expect_gate("serial", [noise], s0), 0)
    chk("--expect: admitted fails (1)", expect_gate("serial", [clean], s0), 1)
    chk("--expect: a different rule fails (1)", expect_gate("serial", [noise], parse_expect("denied:S1")), 1)
    chk("--expect: a superset expectation fails (1)", expect_gate("serial", [noise], parse_expect("denied:S0,S1")), 1)
    with tempfile.TemporaryDirectory() as td:
        raising = os.path.join(td, "raising.py")
        garbage = os.path.join(td, "garbage.py")
        with open(raising, "w") as f:
            f.write("raise ImportError('fixture: the reader does not import')\n")
        with open(garbage, "w") as f:
            f.write("print('this is not json')\n")
        chk("--expect: a raising measurer FAILS (1), never 0", expect_gate("serial", [noise], s0, script=raising), 1)
        chk("--expect: unparseable JSON FAILS (1)", expect_gate("serial", [noise], s0, script=garbage), 1)
    chk("--expect: an absent fixture could not run (3)", expect_gate("serial", [os.path.join(fx, "absent.log")], s0), 3)
    chk("--expect: opa absent could not run (3)", expect_gate("serial", [noise], s0, opa=""), 3)
    chk("--expect: an undefined package FAILS (1)", expect_gate("no_such_policy", [noise], s0, script=measurer("serial")), 1)
    # W75 --denies: the census SEES a negative claim where one exists, and its absence
    d = denies_census()
    chk("--denies sees SERIAL-DENIES on serial", "SERIAL-DENIES" in d.get("serial", []), True)
    chk("--denies reports a gated policy with no negative claim as [] (not absent)",
        any(v == [] for v in d.values()), True)
    print("opa_gate selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
