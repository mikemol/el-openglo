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
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(ROOT, "catalog", "actions.json")

# ⚑ THE HOST TOOLCHAIN IS AN INPUT LIKE ANY OTHER. Each entry is an absolute path
# digested into the key — a binary's bytes, a font's bytes. This is what turns a
# "local, never cached" action into a hermetic one: the Qt that rendered a PNG is
# now IN the key, so a Qt bump invalidates the screens exactly as a template edit
# does. ⚑ THE POPULATION COMES FROM `build_graph.py` UNBUILT, which enumerates
# every host path the tree reaches; anything there and not here is undeclared.
QT_QML = "/usr/lib64/qt6/bin/qml"
HOST_RENDER = (QT_QML, "/usr/share/fonts/hack/Hack-Regular.ttf")

# An action: (name, entry module, data domains, host inputs, output domain, suffixes).
# ⚑ THE DATA DOMAINS ARE DIRECTORIES, NOT FILES, because build_graph measured 39
# undeclared domains — a walk/listdir hides the POPULATION, so naming individual
# files here would re-commit that error one level up.
ACTIONS = (
    ("screens",
     "catalog/library/render_screens.py",
     ("templates", "catalog/library"),
     HOST_RENDER,
     "catalog/library/screens", (".png",)),
    ("schemes",
     "make_schemes.py",
     ("templates",),
     (),
     ".", (".colors",)),
    ("wallpapers",
     "make_wallpaper.py",
     ("templates",),
     (),
     ".", ("-wallpaper.png", "-wallpaper.svg")),
)


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


def key_of(action):
    """(key, inputs, missing) — the digest over the action's whole declared domain.

    ⚑ A DECLARED HOST INPUT THAT IS ABSENT MAKES THE KEY UNCOMPUTABLE, and the
    caller must treat that as `withheld`. Digesting "the files that happened to be
    there" would produce a key that agrees with itself on two different machines
    and silently certifies a cross-host cache hit — the stale green, arrived at by
    the tool built to prevent it."""
    _name, entry, domains, host, _out, _sfx = action
    inputs, missing = {}, []
    for rel in import_closure(entry) + domain_files(domains):
        p = os.path.join(ROOT, rel)
        if os.path.isfile(p):
            inputs[rel] = _digest_file(p)
    for abs_path in host:
        if os.path.isfile(abs_path):
            inputs[f"host:{abs_path}"] = _digest_file(abs_path)
        else:
            missing.append(abs_path)
    h = hashlib.sha256()
    for rel in sorted(inputs):
        h.update(rel.encode() + b"\0" + inputs[rel].encode() + b"\0")
    return h.hexdigest(), inputs, missing


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
        key, inputs, missing = key_of(a)
        outs = outputs_of(a)
        was = recorded.get(name, {})
        cases.append({
            "action": name,
            "key": key,
            "recorded_key": was.get("key"),
            "n_inputs": len(inputs),
            "n_outputs": len(outs),
            "missing_host": missing,
            # ⚑ NO RECORD IS `withheld`, NOT `deny`. Nobody has asserted a build,
            # so currency is UNMEASURED here — not confirmed, and not failed. An
            # absent host input is withheld for the same reason, one level out.
            "state": ("unmeasurable" if missing
                      else "unrecorded" if not was.get("key")
                      else "current" if was["key"] == key
                      else "stale"),
        })
    return {"cases": cases, "manifest": os.path.relpath(MANIFEST, ROOT)}


def write():
    out = {"note": "generated by scripts/action_key.py --write; the key of each "
                   "action's declared input domain at the time its outputs were built",
           "actions": {}}
    for a in ACTIONS:
        key, inputs, missing = key_of(a)
        if missing:
            print(f"action_key: REFUSED to record {a[0]} — declared host input(s) "
                  f"absent: {', '.join(missing)}", file=sys.stderr)
            raise SystemExit(3)
        out["actions"][a[0]] = {"key": key, "n_inputs": len(inputs),
                                "n_outputs": len(outputs_of(a))}
    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
        fh.write("\n")
    return out


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
        key, inputs, _m = key_of(a)
        chk(f"{a[0]}: domain is non-empty", len(inputs) > 0, True)
    # ⚑ THE MEASUREMENT CAN SEE: perturbing one declared input MUST move the key.
    # A currency check whose key never moves is the stale-green this tool exists
    # to stop, wearing the tool's own badge.
    a = ACTIONS[0]
    before, inputs, _m = key_of(a)
    victim = os.path.join(ROOT, sorted(x for x in inputs if not x.startswith("host:"))[0])
    original = open(victim, "rb").read()
    try:
        with open(victim, "ab") as fh:
            fh.write(b"\n# action_key selftest perturbation\n")
        after, _i, _m = key_of(a)
        chk("a changed input moves the key", after != before, True)
    finally:
        with open(victim, "wb") as fh:
            fh.write(original)
    chk("the key is restored with the input", key_of(a)[0], before)
    # ⚑ THE HOST HALF MUST BE IN THE KEY TOO, and an absent one must be VISIBLE
    absent = ("screens-probe", ACTIONS[0][1], ACTIONS[0][2],
              ("/nonexistent/qt/bin/qml",), ACTIONS[0][4], ACTIONS[0][5])
    chk("an absent host input is reported, not ignored", key_of(absent)[2],
        ["/nonexistent/qt/bin/qml"])
    chk("a declared host input is in the domain",
        any(k.startswith("host:") for k in key_of(ACTIONS[0])[1]), True)
    # distinct actions must not collide
    keys = {x[0]: key_of(x)[0] for x in ACTIONS}
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
            key, inputs, missing = key_of(a)
            print(f"  {a[0]:12s} entry={a[1]}")
            print(f"               domains={', '.join(a[2])}  ({len(inputs)} file(s))")
            print(f"               host={', '.join(a[3]) or '(none declared)'}"
                  + (f"  ⚑ ABSENT: {', '.join(missing)}" if missing else ""))
            print(f"               outputs={a[4]}/*{'|*'.join(a[5])}  "
                  f"({len(outputs_of(a))} file(s))")
        return 0
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
        print(f"  {c['state']:11s} {c['action']:12s} "
              f"{c['n_inputs']} input(s), {c['n_outputs']} output(s)")
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
