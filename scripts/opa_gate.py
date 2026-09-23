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
    scripts/opa_gate.py --list           # every policy and whether its check has --json
    scripts/opa_gate.py --test           # opa test policy/ (every rule's refuse/admit pair)
    scripts/opa_gate.py --census [--cpu] # W50: which warrants cite opa_gate vs a bare check_*.py
                                         # (n of m decided in rego); --cpu times each Python one
    scripts/opa_gate.py --selftest

SKIP (exit 0, printed) when opa is absent — a fact about the host. Weakness: the
join is by NAME (check_<name>.py ↔ policy/<name>.rego ↔ package el.<name>); a
policy whose package does not match its file name evaluates to nothing, which
`--selftest` checks for every policy present.
"""
import json
import os
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


def measure(name, operands=()):
    """The check's --json document (a dict), run under this interpreter. `operands`
    (paths, resolved against the repo root) are passed after --json."""
    r = subprocess.run([sys.executable, measurer(name), "--json", *operands],
                       capture_output=True, text=True, cwd=ROOT, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"{os.path.basename(measurer(name))} --json exited {r.returncode}: {r.stderr[-300:]}")
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
    known = {"--list", "--test", "--selftest", "--census", "--cpu"}
    args = [a for a in argv[1:] if a.startswith("--")]
    names = [a for a in argv[1:] if not a.startswith("--")]
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
    print("opa_gate selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
