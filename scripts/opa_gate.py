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
    scripts/opa_gate.py --list           # every policy and whether its check has --json
    scripts/opa_gate.py --test           # opa test policy/ (every rule's refuse/admit pair)
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


def measure(name):
    """The check's --json document (a dict), run under this interpreter."""
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", f"check_{name}.py"), "--json"],
                       capture_output=True, text=True, cwd=ROOT, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"check_{name}.py --json exited {r.returncode}: {r.stderr[-300:]}")
    return json.loads(r.stdout)


def evaluate(name, doc):
    """{'deny': [...], 'withheld': [...]} from opa over the measurement."""
    r = subprocess.run([OPA, "eval", "-f", "json", "-I", "-d", POLICY, f"data.el.{name}"],
                       input=json.dumps(doc), capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"opa eval exited {r.returncode}: {r.stderr[-300:]}")
    res = json.loads(r.stdout)["result"]
    if not res:
        raise RuntimeError(f"data.el.{name} is undefined — no package el.{name} in policy/")
    v = res[0]["expressions"][0]["value"]
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


def main(argv):
    known = {"--list", "--test", "--selftest"}
    args = [a for a in argv[1:] if a.startswith("--")]
    names = [a for a in argv[1:] if not a.startswith("--")]
    for a in args:
        if a not in known:
            print(f"opa_gate: unknown flag {a!r}", file=sys.stderr)
            return 2
    if not OPA:
        print("opa_gate: SKIP — opa is not installed on this host", file=sys.stderr)
        return 0
    if "--list" in args:
        for n in policies():
            has = os.path.isfile(os.path.join(ROOT, "scripts", f"check_{n}.py"))
            print(f"{n:24s} policy/{n}.rego  check_{n}.py {'--json' if has else 'ABSENT'}")
        return 0
    if "--test" in args:
        r = subprocess.run([OPA, "test", POLICY], capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip())
        return r.returncode
    if len(names) != 1:
        print("usage: opa_gate.py <name> | --list | --test | --selftest", file=sys.stderr)
        return 2
    name = names[0]
    sets = evaluate(name, measure(name))
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
        chk(f"{n}: a check with --json exists", os.path.isfile(os.path.join(ROOT, "scripts", f"check_{n}.py")), True)
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
