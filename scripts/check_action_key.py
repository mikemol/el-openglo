#!/usr/bin/env python3
"""action_key.py — the digest of everything an action's output depends on (W61).

⚑ THE DEFECT THIS EXISTS TO STOP, MEASURED 2026-09-22. The operator pointed at
grid glitching in catalog/library/screens/marquee-EL-Openglo.png. It was fixed,
the fix was proven, and the COMMIT CAPTURED THE PRE-FIX PICTURE because the
render had not finished. The operator, on seeing it land: "now the visual artifact
I noticed is fixed. The fact that the updated images didn't go with the commit
hasn't been fixed." A defect they had already pointed at twice recurred because a
verdict was read off a STALE artifact.

⚑ CURRENCY IS A THIRD OBLIGATION, AND NEITHER BOUNDARY SEES IT. build_graph.py
asks whether a file is PRODUCED and whether it is CONSUMED. A file can be both and
still be wrong, because it was produced by a version of its producer that no longer
exists. Produced ∧ consumed ∧ CURRENT — and only the first two are topological.

⚑ IT IS `check_template_parity` GENERALISED, AND THAT IS WHY IT IS NOT NEW
MACHINERY. That check re-emits a template and compares bytes to a recorded
baseline; it caught an ApertureField edit within seconds. It works because a
template is CHEAP to re-emit. A 48-render screens sweep is not, so the comparison
moves from the OUTPUT to the INPUTS: record the key at emission, check the key at
commit. Same obligation, affordable witness.

    scripts/action_key.py --list             # the declared actions and their domains
    scripts/action_key.py --write            # record every action's key (after a build)
    scripts/action_key.py --check            # is each recorded key still current?
    scripts/action_key.py --json             # the measurement, for policy/action_key.rego
    scripts/action_key.py --selftest         # the measurement can SEE a stale key

⚑ THE DOMAIN IS DECLARED BY OVER-APPROXIMATION, DELIBERATELY. An action names its
entry module (whose repo-local import closure is computed exactly) and its DATA
DIRECTORIES, every file of which is digested whether or not that run read it. This
is the fail-safe direction: an over-wide domain reports an artifact stale when it
is merely untouched, which costs a rebuild. An under-wide domain reports it current
when it is not, which is the defect above. ⚑ Π-TYPED MEANS THE DECLARED INPUTS
COVER THE FULL DOMAIN THE VERDICT RANGES OVER — not that they are minimal.

⚑ A HOST INPUT IS DECLARED, NOT EXCUSED (operator, 2026-09-22, correcting this
file's first draft — which said a rendering action is host-coupled and "must never
be cached"): "Remember what I said about caching. It's only unsound if dependencies
are undeclared. So declare your dependencies." Calling an action `local` because it
touches Qt reads a gap in DECLARATION as a property of the SUBSTRATE — the same
error as reading *no match found* as *no such thing exists*. There is no
uncacheable action here, only an undeclared one. So each action names its HOST
domain too, and `build_graph.py`'s UNBUILT list is precisely the worklist for that:
36 host inputs measured 2026-09-22, every one of them a cache key nobody wrote down.

WEAKNESS, STATED: this proves the DECLARED inputs have not changed since the
outputs were recorded. It does NOT prove the outputs were ever correct, nor that
the recorded key was written after a run that actually completed — `--write` is an
assertion by whoever runs it. And a host input that is ABSENT is `withheld`, never
skipped silently: an unreadable font is a fact about the machine, so the key cannot
be computed and must not be pretended.
"""
import ast
import hashlib
import json
import os
import subprocess
import sys
from typing import NamedTuple

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ⚑ NO sys.path SURGERY (operator, 2026-09-22: "Do not do the sys.path.insert
# thing. Instead, take everything you WOULD import and build a package out of
# it"). A sys.path.insert is an import that works only because of how the process
# was launched — the same class as a symlinked tool deriving its root from
# abspath(__file__), which mtools records breaking silently for exactly that
# reason. This plain import resolves because both modules sit in scripts/; it is
# correct by LAYOUT rather than by patching the interpreter, and it is a stopgap:
# ⚑ THE REAL ANSWER IS A DISTRIBUTION (W62), on mtools' shape — src/mikemol/<n>/,
# PEP 420 implicit namespace, console scripts as the adoption path that replaces
# a symlink, dependencies published or git-pinned and NEVER editable/path.
import build_graph  # noqa: E402
MANIFEST = os.path.join(ROOT, "catalog", "actions.json")

# ⚑ YOU DO NOT DECLARE A HOST BINARY. YOU DEFINE YOUR HOST (operator, 2026-09-22,
# correcting this file's second draft). Enumerating host FILES — the qml binary,
# one font — is declaring EDGES where the thing that needs declaring is a DOMAIN,
# the same defect build_graph found in a bare `walk()`. A Qt render's real domain
# is every shared library, fontconfig rule, locale, Qt plugin and codec the
# process can see; that list is not closeable by hand, and a key built from two of
# its members AGREES WITH ITSELF ACROSS TWO DIFFERENT MACHINES while looking
# complete. An image digest is complete by construction; a file list never is.
#
# So the host half of the key is ONE identity, and it is honest about which kind
# it is. PINNED: a container image digest, which licenses cross-host reuse.
# UNPINNED: a fingerprint of this machine, which is enough to notice that the host
# MOVED under us but does NOT license transporting a cached verdict anywhere else.
# ⚑ THE DISTINCTION IS THE POINT — not-transferable is a fact about the
# declaration, and it must not be silently upgraded by pretending.
# ⚑ A KEY-FORMULA CHANGE IS NOT AN ARTIFACT CHANGE, and reporting one as the other
# is a false accusation the reader cannot check. Measured 2026-09-22: replacing the
# host FILE LIST with a host IDENTITY moved every host-seeing key, and the tool
# said "screens is STALE — rebuild", though nothing in the screens domain had
# moved. A digest over a changed formula is a different question, not a worse
# answer to the same one. Bump this whenever what goes INTO the key changes.
KEY_SCHEMA = 2

HOST_PIN_FILE = os.path.join(ROOT, "catalog", "host.json")

# a fingerprint of the unpinned host: cheap, and NOT claimed to be complete
HOST_FINGERPRINT_SOURCES = (
    "/etc/os-release",
    "/usr/lib64/qt6/bin/qml",
    "/usr/share/fonts/hack/Hack-Regular.ttf",
)

# An action: (name, entry module, data domains, host inputs, output domain, suffixes).
# ⚑ THE DATA DOMAINS ARE DIRECTORIES, NOT FILES, because build_graph measured 39
# undeclared domains — a walk/listdir hides the POPULATION, so naming individual
# files here would re-commit that error one level up.
# An action: (name, entry module, data domains, sees_host, output domain, suffixes).
# ⚑ `sees_host` IS A BOOLEAN, NOT A LIST. Either the action's verdict can depend on
# the machine it ran on — in which case the WHOLE host is in its domain and the
# host identity goes in its key — or it cannot. There is no partial host.
ACTIONS = (
    ("screens",
     "catalog/library/render_screens.py",
     ("templates", "catalog/library"),
     True,                                  # Qt renders it: the host is the domain
     "catalog/library/screens", (".png",)),
    ("schemes",
     "make_schemes.py",
     ("templates",),
     False,                                 # pure Python over the palette
     ".", (".colors",)),
    ("wallpapers",
     "make_wallpaper.py",
     ("templates",),
     False,
     ".", ("-wallpaper.png", "-wallpaper.svg")),
)


def host_identity():
    """(kind, id, detail) — WHICH host this tree's artifacts were built on.

    kind is "pinned" when catalog/host.json records an image digest (the
    executor image the render ran in, `repo@sha256:...`, with a `source` naming
    where it came from — luthen's image-pin shape, which they report as the
    adoptable half of their RBE setup). Then the id covers the whole filesystem
    the action sees, and a cache hit is transportable.

    kind is "unpinned" otherwise: a fingerprint over a few host files, which can
    detect that THIS machine moved and must never be read as hermeticity. ⚑ AN
    UNPINNED HOST IS NOT A FAILURE — it is the state this repo is in today, and
    saying so is the difference between a measurement and a pretence."""
    if os.path.isfile(HOST_PIN_FILE):
        pin = json.load(open(HOST_PIN_FILE, encoding="utf-8"))
        digest = pin.get("image")
        if digest and "@sha256:" in digest:
            return "pinned", digest, pin.get("source", "(no source recorded)")
        return "unmeasurable", None, f"{HOST_PIN_FILE} has no `image` with an @sha256: digest"
    h = hashlib.sha256()
    seen = []
    for p in HOST_FINGERPRINT_SOURCES:
        if os.path.isfile(p):
            h.update(p.encode() + b"\0" + _digest_file(p).encode() + b"\0")
            seen.append(p)
    if not seen:
        # ⚑ REFUSE AN EMPTY POPULATION. A fingerprint over nothing is a constant,
        # and every host would agree with every other host forever.
        return "unmeasurable", None, "no host fingerprint source is readable"
    return "unpinned", h.hexdigest(), f"{len(seen)} of {len(HOST_FINGERPRINT_SOURCES)} source(s)"


def _digest_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def import_closure(entry):
    """Every repo-local .py the entry module transitively imports, sorted.

    ⚑ EXACT, UNLIKE THE DATA DOMAIN. An import is a literal in the source, so the
    code half of the domain needs no over-approximation — which matters, because
    the code half is what actually changed in the incident above."""
    seen, stack = set(), [entry]
    while stack:
        rel = stack.pop()
        if rel in seen or not os.path.isfile(os.path.join(ROOT, rel)):
            continue
        seen.add(rel)
        try:
            tree = ast.parse(open(os.path.join(ROOT, rel), encoding="utf-8").read())
        except SyntaxError:
            continue
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names.add(node.module)
        for n in names:
            parts = n.split(".")
            for base in ("", "scripts", os.path.dirname(rel), "catalog/library"):
                cand = os.path.join(base, *parts) + ".py"
                if os.path.isfile(os.path.join(ROOT, cand)):
                    stack.append(os.path.normpath(cand))
                    break
    return sorted(seen)


def domain_files(domains):
    """Every file under each declared data domain, sorted. The over-approximation."""
    out = []
    for d in domains:
        base = os.path.join(ROOT, d)
        if os.path.isfile(base):
            out.append(d)
            continue
        for b, dirs, names in os.walk(base):
            dirs[:] = [x for x in dirs
                       if x not in {".git", "__pycache__", "screens", ".venv", "node_modules"}]
            for n in sorted(names):
                if n.endswith((".pyc", ".json")):
                    continue
                out.append(os.path.relpath(os.path.join(b, n), ROOT))
    return sorted(set(out))


class Key(NamedTuple):
    """A key AND the two ways its domain scan under-covered — never one without
    the others.

    ⚑ THE CALLER MUST NOT BE ABLE TO RECEIVE SUCCESS WITHOUT THE GAP SETS
    (linux-sources-9c, 2026-09-22, handing over the decision this repo asked to
    inherit): "the trap for a closure tool is not 'the closure is wrong'; it is
    'the closure dropped an unresolvable import and returned success', so the
    caller reads absence-of-error as coverage."

    ⚑ AND THIS TOOL WAS ALREADY IN THAT TRAP, COMMITTED AT b98f8cc THIS MORNING.
    key_of digested an exact import closure plus a directory walk and returned a
    clean `(key, inputs, missing)` — where `missing` covered ONLY an absent host
    file. The entry module's computed reads (61 across this tree) and undeclared
    domains (42) were never mentioned, so the key looked complete and every
    caller read it as currency. The residue rides in the return type now.

    ⚑ OVER-FIRING HERE IS SAFE, AND THAT IS THE ASYMMETRY TO BIAS ON. Over-
    approximating the DEPENDENCY set has no terminating condition; over-
    approximating the RESIDUE set does. A false positive costs one file declared
    uncovered; a false negative costs a wrong verdict."""
    key: str
    inputs: dict
    missing_host: list
    unresolved: list          # edges the scan could not resolve, `file:line: why`
    undeclared_domains: list  # glob/walk/listdir sites: the population is unknown


def key_of(action):
    """A Key over the action's whole declared domain, carrying its own residue.

    ⚑ A DECLARED HOST INPUT THAT IS ABSENT MAKES THE KEY UNCOMPUTABLE, and the
    caller must treat that as `withheld`. Digesting "the files that happened to be
    there" would produce a key that agrees with itself on two different machines
    and silently certifies a cross-host cache hit — the stale green, arrived at by
    the tool built to prevent it.

    ⚑ THE RESIDUE IS UNIONED ALONG THE CLOSURE, not taken at the entry module. An
    edge unresolvable at ANY depth is named, because a computed read three imports
    down reaches the artifact exactly as one in the entry does."""
    _name, entry, domains, sees_host, _out, _sfx = action
    inputs, missing = {}, []
    closure = import_closure(entry)
    for rel in closure + domain_files(domains):
        p = os.path.join(ROOT, rel)
        if os.path.isfile(p):
            inputs[rel] = _digest_file(p)
    unresolved, undeclared = [], []
    for rel in closure:
        for line, direction, why in build_graph.computed_edges(rel):
            site = f"{rel}:{line}: {why}"
            (undeclared if direction == "domain" else unresolved).append(site)
    if sees_host:
        kind, hid, detail = host_identity()
        if kind == "unmeasurable":
            missing.append(detail)
        else:
            inputs[f"host:{kind}"] = hid
    h = hashlib.sha256()
    for rel in sorted(inputs):
        h.update(rel.encode() + b"\0" + inputs[rel].encode() + b"\0")
    return Key(h.hexdigest(), inputs, missing, sorted(unresolved), sorted(undeclared))


def declared_outputs(action):
    """The outputs the ACTION ITSELF declares, or None when it declares none.

    ⚑ A DIRECTORY LISTING IS NOT A DECLARATION, and conflating them hides exactly
    the defect this found. Measured 2026-09-22: render_screens' `--list` printed
    36 files while the action wrote 55 — the 12 animations, the 7 contact sheets
    and a README were produced and declared nowhere. Keying on the DIRECTORY
    would have agreed with itself no matter how wrong the plan was, because it
    measures the disk rather than the claim. ⚑ AND THE DECLARATION IS THE
    PRECONDITION FOR SPLITTING: one backward cone per output requires the outputs
    to be enumerable from the plan, so an undeclared output is one whose
    staleness nobody can attribute."""
    entry = os.path.join(ROOT, action[1])
    r = subprocess.run([sys.executable, entry, "--outputs"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        return None                      # the action declares no output roster
    try:
        return sorted(o["file"] for o in json.loads(r.stdout)["outputs"])
    except (ValueError, KeyError):
        return None


def outputs_of(action):
    """The artifact paths this action is declared to produce, sorted."""
    _n, _e, _d, _h, outdir, sfx = action
    base = os.path.join(ROOT, outdir)
    if not os.path.isdir(base):
        return []
    return sorted(os.path.relpath(os.path.join(base, n), ROOT)
                  for n in os.listdir(base) if n.endswith(sfx))


def measure():
    """{action: {key, recorded, outputs, current}} — what IS, not what should be."""
    recorded = {}
    if os.path.isfile(MANIFEST):
        recorded = json.load(open(MANIFEST, encoding="utf-8")).get("actions", {})
    cases = []
    for a in ACTIONS:
        name = a[0]
        k = key_of(a)
        key, missing = k.key, k.missing_host
        outs = outputs_of(a)
        # the output boundary, both directions — declared vs present
        declared = declared_outputs(a)
        present = {os.path.basename(p) for p in outs}
        undeclared = [] if declared is None else sorted(present - set(declared))
        absent = [] if declared is None else sorted(
            f for f in declared if f.endswith(a[5])
            and not os.path.isfile(os.path.join(ROOT, a[4], f)))
        was = recorded.get(name, {})
        cases.append({
            "action": name,
            "key": key,
            "recorded_key": was.get("key"),
            "n_inputs": len(k.inputs),
            "n_outputs": len(outs),
            "missing_host": missing,
            # ⚑ THE RESIDUE TRAVELS WITH THE MEASUREMENT, so the policy can
            # WITHHOLD rather than admit a key whose domain scan under-covered.
            "n_unresolved": len(k.unresolved),
            "n_undeclared_domains": len(k.undeclared_domains),
            "unresolved": k.unresolved[:5],
            "undeclared_domains": k.undeclared_domains[:5],
            # ⚑ ∂ AT THE OUTPUT BOUNDARY: what the action SAYS it writes against
            # what is on disk. Undeclared files are outputs nobody can attribute a
            # staleness to; declared-but-absent are a build that did not finish —
            # which is the original incident, seen from the other side.
            "undeclared_outputs": undeclared,
            "declared_absent": absent,
            # ⚑ NO RECORD IS `withheld`, NOT `deny`. Nobody has asserted a build,
            # so currency is UNMEASURED here — not confirmed, and not failed. An
            # absent host input is withheld for the same reason, one level out.
            "sees_host": a[3],
            "state": ("unmeasurable" if missing
                      else "unrecorded" if not was.get("key")
                      # the recorded key answers a DIFFERENT question than this one
                      else "reformulated" if was.get("schema") != KEY_SCHEMA
                      else "current" if was["key"] == key
                      else "stale"),
        })
    kind, _hid, detail = host_identity()
    return {"cases": cases, "manifest": os.path.relpath(MANIFEST, ROOT),
            "host": {"kind": kind, "detail": detail}}


def write():
    out = {"note": "generated by scripts/action_key.py --write; the key of each "
                   "action's declared input domain at the time its outputs were built",
           "actions": {}}
    for a in ACTIONS:
        k = key_of(a)
        if k.missing_host:
            print(f"action_key: REFUSED to record {a[0]} — declared host input(s) "
                  f"absent: {', '.join(k.missing_host)}", file=sys.stderr)
            raise SystemExit(3)
        # ⚑ THE RESIDUE IS RECORDED WITH THE KEY, not merely reported beside it.
        # A manifest that stores only the digest cannot tell a later reader how
        # much of the domain that digest actually covered — so a key recorded
        # while 21 edges were unresolved would read, a month later, exactly like
        # one recorded over a fully-resolved domain.
        out["actions"][a[0]] = {"key": k.key, "schema": KEY_SCHEMA,
                                "n_inputs": len(k.inputs),
                                "n_unresolved": len(k.unresolved),
                                "n_undeclared_domains": len(k.undeclared_domains),
                                "n_outputs": len(outputs_of(a))}
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return out


def _write_is_callable():
    """Does write()'s body still agree with key_of's return type?

    ⚑ EXERCISED AGAINST A SCRATCH MANIFEST, never the real one: a selftest that
    records keys would ASSERT A BUILD, which is the one thing --write means."""
    import tempfile
    global MANIFEST
    real = MANIFEST
    try:
        with tempfile.TemporaryDirectory() as d:
            MANIFEST = os.path.join(d, "actions.json")
            write()
        return True
    except (TypeError, ValueError, AttributeError):
        return False
    finally:
        MANIFEST = real


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}"
              + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    print("action_key selftest:")
    # ⚑ THE POPULATION IS NOT EMPTY — a key over nothing is a constant, and three
    # actions all keyed on an empty domain would agree with each other forever.
    for a in ACTIONS:
        k = key_of(a)
        chk(f"{a[0]}: domain is non-empty", len(k.inputs) > 0, True)
    # ⚑ THE MEASUREMENT CAN SEE: perturbing one declared input MUST move the key.
    # A currency check whose key never moves is the stale-green this tool exists
    # to stop, wearing the tool's own badge.
    a = ACTIONS[0]
    base = key_of(a)
    victim = os.path.join(ROOT, sorted(x for x in base.inputs if not x.startswith("host:"))[0])
    original = open(victim, "rb").read()
    try:
        with open(victim, "ab") as fh:
            fh.write(b"\n# action_key selftest perturbation\n")
        chk("a changed input moves the key", key_of(a).key != base.key, True)
    finally:
        with open(victim, "wb") as fh:
            fh.write(original)
    chk("the key is restored with the input", key_of(a).key, base.key)
    # ⚑ THE HOST HALF MUST BE IN THE KEY TOO, and an absent one must be VISIBLE
    chk("a host-seeing action carries a host identity",
        any(k.startswith("host:") for k in key_of(ACTIONS[0]).inputs), True)
    chk("a pure action carries NO host identity",
        any(k.startswith("host:") for k in key_of(ACTIONS[1]).inputs), False)
    # ⚑ THE HOST HALF MUST MOVE THE KEY, or declaring it is decoration
    pure = ("screens-pure", ACTIONS[0][1], ACTIONS[0][2], False, ACTIONS[0][4], ACTIONS[0][5])
    chk("dropping the host changes the key", key_of(pure).key != key_of(ACTIONS[0]).key, True)
    # ⚑ THE RESIDUE MUST BE NON-EMPTY AND MUST RIDE WITH THE KEY. If this ever
    # reads zero, the scanner stopped looking — not the tree got clean.
    chk("the key carries its residue as fields",
        set(Key._fields), {"key", "inputs", "missing_host", "unresolved", "undeclared_domains"})
    chk("the screens residue is non-empty (its emitter computes paths)",
        len(base.unresolved) + len(base.undeclared_domains) > 0, True)
    # ⚑ THE OUTPUT BOUNDARY MUST BE MEASURABLE, AND ITS ABSENCE DISTINGUISHABLE
    # FROM AGREEMENT. An action with no --outputs roster returns None, which is
    # "not declared"; an action with one returns a list, which can then disagree.
    # If these two ever render the same, the check reads an undeclared action as
    # a conforming one — the defect that let render_screens write 19 files nobody
    # had named.
    # ⚑ EVERY MODE IS EXERCISED, BECAUSE A MODE NOBODY RUNS IS A MODE NOBODY
    # TYPED. Measured 2026-09-22: `write()` still unpacked key_of as a 3-tuple
    # hours after the Key type landed, and every other call site had been fixed.
    # It survived because the selftest called measure() and never write() — so
    # the suite was green while `--write` raised ValueError on its first use.
    chk("write() agrees with the Key type", _write_is_callable(), True)
    # ⚑ EVERY READ-ONLY MODE IS RUN, BECAUSE CHOOSING WHICH TO RUN IS JUDGEMENT IN
    # THE TURN. Measured 2026-09-22: the Key NamedTuple broke FOUR call sites and
    # each was found by someone running a mode by hand — write(), a selftest, one
    # --list, and then check_action_key's OWN --list, which a delegated census hit
    # hours later with `ValueError: too many values to unpack`. After the third I
    # said I had censused the call sites; I had censused a DIFFERENT tool's. The
    # gate never saw it because @CURRENCY drives --json and --list is a separate
    # arm. ⚑ --write and --selftest are excluded deliberately: one ASSERTS A BUILD,
    # the other recurses.
    for mode in ("--list", "--json"):
        r = subprocess.run([sys.executable, os.path.abspath(__file__), mode],
                           capture_output=True, text=True, cwd=ROOT)
        chk(f"mode {mode} runs", (r.returncode, "Traceback" in r.stderr), (0, False))
    chk("an action that declares its outputs yields a roster",
        isinstance(declared_outputs(ACTIONS[0]), list), True)
    chk("an action that declares none is None, not an empty roster",
        declared_outputs(ACTIONS[1]), None)
    kind, _hid, _d = host_identity()
    chk("the host identity names its own kind", kind in ("pinned", "unpinned"), True)
    print(f"  note  host is {kind} — "
          + ("a cache hit is transportable" if kind == "pinned"
             else "staleness is detectable HERE; cross-host reuse is NOT licensed"))
    # distinct actions must not collide
    keys = {x[0]: key_of(x).key for x in ACTIONS}
    chk("distinct actions have distinct keys", len(set(keys.values())), len(ACTIONS))
    print("action_key selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    known = {"--list", "--write", "--check", "--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"action_key: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return _selftest()
    if "--write" in argv:
        out = write()
        for name, rec in sorted(out["actions"].items()):
            print(f"  {name:12s} key={rec['key'][:16]}  "
                  f"{rec['n_inputs']} input(s) -> {rec['n_outputs']} output(s)")
        print(f"action_key: recorded {len(out['actions'])} action(s) "
              f"in {os.path.relpath(MANIFEST, ROOT)}")
        return 0
    m = measure()
    if "--json" in argv:
        print(json.dumps(m, indent=1))
        return 0
    if "--list" in argv:
        for a in ACTIONS:
            k = key_of(a)
            print(f"  {a[0]:12s} entry={a[1]}")
            print(f"               domains={', '.join(a[2])}  ({len(k.inputs)} file(s))")
            print(f"               host={'the whole host' if a[3] else '(none declared)'}"
                  + (f"  ⚑ UNCOMPUTABLE: {', '.join(k.missing_host)}" if k.missing_host else ""))
            print(f"               residue={len(k.unresolved)} unresolved, "
                  f"{len(k.undeclared_domains)} undeclared domain(s)")
            print(f"               outputs={a[4]}/*{'|*'.join(a[5])}  "
                  f"({len(outputs_of(a))} file(s))")
        return 0
    host = m["host"]
    print(f"  host: {host['kind']} — {host['detail']}")
    if host["kind"] == "unpinned":
        print("    ⚑ staleness is detectable on THIS machine only; a cached verdict is")
        print("      not transportable. Build oci/Containerfile and record its digest")
        print("      in catalog/host.json to license that.")
    cases = m["cases"]
    stale = [c for c in cases if c["state"] == "stale"]
    unrec = [c for c in cases if c["state"] == "unrecorded"]
    unmeas = [c for c in cases if c["state"] == "unmeasurable"]
    if unmeas:
        print(f"\naction_key: WITHHELD — {len(unmeas)} of {len(cases)} action(s) declare "
              f"a host input absent on this machine:", file=sys.stderr)
        for c in unmeas:
            print(f"    {c['action']}: {', '.join(c['missing_host'])}", file=sys.stderr)
        if len(unmeas) == len(cases):
            return 3
    for c in cases:
        gap = c["n_unresolved"] + c["n_undeclared_domains"]
        print(f"  {c['state']:11s} {c['action']:12s} "
              f"{c['n_inputs']} input(s), {c['n_outputs']} output(s)"
              + (f"  ⚑ residue: {c['n_unresolved']} unresolved edge(s), "
                 f"{c['n_undeclared_domains']} undeclared domain(s)" if gap else ""))
        for s in c["unresolved"] + c["undeclared_domains"]:
            print(f"                  {s}")
    if stale:
        print(f"\naction_key: REFUSED — {len(stale)} of {len(cases)} action(s) STALE: "
              f"the outputs in the tree were built from inputs that have since changed.",
              file=sys.stderr)
        for c in stale:
            print(f"    {c['action']}: recorded {c['recorded_key'][:16]} "
                  f"but the domain now keys {c['key'][:16]}", file=sys.stderr)
        print("  rebuild, then: scripts/action_key.py --write", file=sys.stderr)
        return 1
    if unrec and len(unrec) == len(cases):
        print(f"\naction_key: WITHHELD — {len(unrec)} of {len(cases)} action(s) have no "
              f"recorded key; currency is UNMEASURED, not confirmed.", file=sys.stderr)
        return 3
    if unrec:
        print(f"\naction_key: SKIP for {len(unrec)} of {len(cases)} unrecorded action(s); "
              f"{len(cases) - len(unrec)} current")
        return 0
    print(f"\naction_key: {len(cases)} of {len(cases)} action(s) current — "
          f"every declared input matches the key recorded at build time")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
