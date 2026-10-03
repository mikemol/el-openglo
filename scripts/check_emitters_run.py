#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_emitters_run.py — the generators actually RUN, and what they emit IS what is tracked.

⚑ THE WITNESS THAT WOULD HAVE CAUGHT THE PARTIAL FILES.  check_compiles.py passes
every one of these, and said so in its own docstring: compiling proves the syntax
survived the recovery and nothing more.  Three real defects hid behind it, all in
files the archive marked ** PARTIAL **, none of them a syntax error:

  · make_schemes.py  — a module-level forward reference (a duplicated solver-flag
    block placed BEFORE the table it reads), plus a mangled identifier
    `_AUTHORED__AUTHORED_GRID` from a mis-anchored replay edit.  NameError at import.
  · make_konsole.py  — called `reference_floors()` (plural, dict-shaped); cvd_gate
    defines `reference_floor()` returning a tuple.  AttributeError at run.
  · make_chrome.py   — its __main__ named six variants before the schemes that
    define them had been emitted.

⚑ IT NO LONGER WRITES INTO THE TREE (W68, 2026-09-23).  It ran each emitter as
__main__ in ROOT, and make_schemes rewrote the TRACKED EL-*.colors while ~20
parallel checks read them through make_preview.parse_scheme: a torn read failed a
check that passed on replay.  emitters.atomic_write fixes the tear but not the
race over WHICH version a reader sees — a gate must not mutate its own inputs.

So this is REGENERATE-AND-COMPARE, like paperkit's projections: the tracked tree
(git ls-files) plus the palette cache is copied into a private tempdir, every
emitter runs THERE — ROOT and cwd both resolve to the copy, so every emitter is
redirected without a per-emitter output flag — and each tracked file the run
changed is DRIFT, reported with a diff summary.  The real tree's tracked files
are fingerprinted (inode, mtime_ns, size) before and after; any change is itself
a deny, so "does not write the tree" is measured, not asserted.

    scripts/check_emitters_run.py              # exit 0 iff each runs and nothing drifts
    scripts/check_emitters_run.py --json       # the measurement, for policy/emitters_run.rego
    scripts/check_emitters_run.py --list       # the order they run in, and why
    scripts/check_emitters_run.py --selftest   # the comparison can SEE drift and a tree write
    scripts/check_emitters_run.py --apply      # adopt every drifted TRACKED file from the run, atomically

⚑ --apply IS THE MECHANICAL ANSWER TO "WHAT MUST I REBUILD" (2026-10-03). A template
edit moves every tracked output that bundles it (the clock plasmoid's SegmentChar.qml
drifted when SegmentChar changed, and a hand-run of make_schemes and make_wallpaper had
not covered it). Instead of reasoning about the emitters' dependencies, run the whole
pipeline in the private copy and ADOPT what drifted: the run IS the dependency tree. It
refuses when any emitter failed (a half-run pipeline is not the pipeline), refuses a
path the run deleted or relinked, writes through emitters.atomic_write, and lists every
adopted path with its diff for review. It does NOT adopt untracked outputs (stated below),
and it is the integrator's explicit act: the gate itself still never writes the tree.

⚑ ORDER IS A FACT ABOUT THE PIPELINE, NOT A PREFERENCE.  make_schemes writes the
`.colors` files every token-reading emitter then parses, so it goes first.

⚑ AN EMITTER WHOSE EXTERNAL INPUT IS ABSENT IS A SKIP, COUNTED AND NAMED.

WEAKNESSES, stated: (1) An emitter that writes an ABSOLUTE path outside ROOT is
not redirected by the copy (make_preview's __main__ demo writes /tmp/preview-*.png;
make_kvantum reads /tmp/KvFlat.kvconfig); those land where they always did, and
never in the tree. (2) Untracked outputs (gitignored build products) are counted
but not compared: there is no tracked version to compare against. (3) The tree
fingerprint covers TRACKED files only. (4) The default (non --json) mode repeats
the policy's judgement in Python; opa_gate.py emitters_run is the authority.
"""

import difflib
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ⚑ THE ROSTER LIVES IN emitters.py, READ BY THIS GATE AND BY make_deb.stage().
sys.path.insert(0, ROOT)
from emitters import EXTERNAL, ORDER

CACHE = ".palette-cache.json"  # untracked, but the solve it saves is ~108 s CPU


# ⚑ SESSION STATE IS NOT TREE CONTENT (measured 2026-09-23). E3 flaked twice: each
# time the paths-forward loop rewrote its TRACKED ledger (.claude/paths-forward.*)
# during the gate — the operator's live session record, written concurrently BY
# DESIGN, and nothing an emitter can produce. E2 had the same exposure (the copy is
# taken at the start, compared at the end). What E2/E3 judge is what an EMITTER can
# write, so the session's own directory is outside both populations, by
# declaration. An emitter that wrote into .claude/ would be a defect this cannot
# see — stated, not hidden; check_atomic_writes' census of emitter writes can.
SESSION_STATE = (".claude/",)


def tracked(root):
    """Every tracked path under `root`, relative, minus session state —
    scripts/git_tracked.py, the ONE population authority (W61 N4; this was a second
    `git ls-files -z` copy). It scrubs GIT_DIR/GIT_INDEX_FILE for a root that is not
    this repo, and walks where there is no git (the Δ sandbox), where the copy here
    raised. SESSION_STATE (above) is then removed, by declaration."""
    import git_tracked

    return [p for p in git_tracked.files(root=root) if not p.startswith(SESSION_STATE)]


def fingerprint(root, paths):
    """{path: (inode, mtime_ns, size)} — what a write, even a same-bytes one, changes."""
    out = {}
    for p in paths:
        try:
            st = os.lstat(os.path.join(root, p))
            out[p] = (st.st_ino, st.st_mtime_ns, st.st_size)
        except OSError:
            out[p] = None
    return out


def _read(path):
    """The bytes a tracked path holds — for a SYMLINK, its target, as git tracks it
    (the borrowed tools link to ../../substrate, which does not resolve in a copy)."""
    try:
        if os.path.islink(path):
            return b"symlink -> " + os.readlink(path).encode("utf-8")
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def diff_summary(a, b, name):
    """A short unified diff for text, a size line for binary."""
    try:
        at, bt = a.decode("utf-8").splitlines(), b.decode("utf-8").splitlines()
    except (UnicodeDecodeError, AttributeError):
        return f"binary: {len(a or b'')} -> {len(b or b'')} bytes"
    d = list(
        difflib.unified_diff(
            at, bt, f"tracked/{name}", f"emitted/{name}", n=0, lineterm=""
        )
    )
    return "\n".join(d[:12]) + (
        f"\n… {len(d) - 12} more diff line(s)" if len(d) > 12 else ""
    )


def copy_tree(src, dst, paths):
    for p in paths + [CACHE]:
        s = os.path.join(src, p)
        if os.path.islink(s) or os.path.isfile(s):
            d = os.path.join(dst, p)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(
                s, d, follow_symlinks=False
            )  # atomic-write: exempt — into a private tempdir


def run_in(copy, mod, timeout=600):
    """(rc, last stderr line) of `mod` run as __main__ inside `copy`.

    ⚑ THE GATE'S `schemes` ARTIFACT IS UN-DECLARED HERE (W75). This copy is a private
    BUILD: its make_schemes emits the copy's own .colors and every later emitter must
    read THOSE. Inheriting the gate's snapshot would feed the tracked palette to the
    emitters downstream of a re-solve, and a drift in make_schemes would be judged
    against outputs that never saw it."""
    import schemes_artifact

    r = subprocess.run(
        [sys.executable, os.path.join(copy, mod + ".py")],
        cwd=copy,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
        env=schemes_artifact.with_declared(os.environ, None),
    )
    tail = (r.stderr or r.stdout).strip().splitlines()
    return r.returncode, (tail[-1] if tail else f"exit {r.returncode}")


def adopt_drift(root, copy, drift, cases):
    """Adopt each drifted tracked file from the private `copy` into the real tree, atomically.
    Returns (adopted paths, refusals). REFUSES the whole adoption when any emitter failed
    (a half-run pipeline's output is not the pipeline's), and refuses a path the run
    DELETED or turned into a symlink (a rebuild must not remove or relink tracked files)."""
    from emitters import atomic_write

    failed = [c["module"] for c in cases if c["rc"] != 0]
    if failed:
        return [], [f"an emitter failed ({', '.join(failed)}): nothing adopted"]
    adopted, refused = [], []
    for d in drift:
        src = os.path.join(copy, d["path"])
        if not os.path.isfile(src) or os.path.islink(src):
            refused.append(
                f"{d['path']}: the run deleted it or made it a link; not adopted"
            )
            continue
        with open(src, "rb") as fh:
            atomic_write(os.path.join(root, d["path"]), fh.read())
        adopted.append(d["path"])
    return adopted, refused


def measure(root=ROOT, order=ORDER, external=EXTERNAL, mutate=None, adopt=False):
    """The --json document. `mutate(copy)` runs after the emitters (selftest hook).
    `adopt` (the --apply mode) writes each drifted tracked file into the real tree
    after the comparison; those writes are intended and not reported as tree_touched."""
    paths = tracked(root)
    before = fingerprint(root, paths)
    cases, withheld, drift, untracked_new = [], [], [], 0
    adopted, refused = [], []
    with tempfile.TemporaryDirectory(prefix="el-emitters-") as copy:
        copy_tree(root, copy, paths)
        for mod, _why in order:
            if not os.path.exists(os.path.join(copy, mod + ".py")):
                cases.append(
                    {"module": mod, "rc": None, "detail": "module file absent"}
                )
                continue
            rc, detail = run_in(copy, mod)
            cases.append({"module": mod, "rc": rc, "detail": detail})
        for mod, (need, why) in external.items():
            if os.path.exists(need):
                rc, detail = run_in(copy, mod)
                cases.append({"module": mod, "rc": rc, "detail": detail})
            else:
                withheld.append({"module": mod, "withheld": f"needs {need} — {why}"})
        if mutate:
            mutate(copy)
        for p in paths:
            a, b = _read(os.path.join(root, p)), _read(os.path.join(copy, p))
            if a != b:
                drift.append(
                    {
                        "path": p,
                        "summary": diff_summary(a, b, p)
                        if b is not None
                        else "deleted by the run",
                    }
                )
        if adopt:
            adopted, refused = adopt_drift(root, copy, drift, cases)
        seen = set(paths)
        # population: the private tempdir copy — counting what the emitters wrote there that is NOT tracked is the point
        for dp, _dn, fs in os.walk(copy):
            for f in fs:
                if os.path.relpath(os.path.join(dp, f), copy) not in seen:
                    untracked_new += 1
    after = fingerprint(root, paths)
    touched = sorted(p for p in paths if before[p] != after[p] and p not in adopted)
    return {
        "cases": cases,
        "withheld": withheld,
        "drift": drift,
        "tree_touched": touched,
        "tracked": len(paths),
        "untracked_emitted": untracked_new,
        "adopted": adopted,
        "refused": refused,
    }


def main(argv):
    known = {"--list", "--json", "--apply"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_emitters_run: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--apply" in argv:
        if len(argv) != 2:
            print("check_emitters_run: --apply takes no other flag", file=sys.stderr)
            return 2
        doc = measure(adopt=True)
        failed = [c for c in doc["cases"] if c["rc"] != 0]
        for c in failed:
            print(f"    FAILED {c['module']}: {c['detail']}", file=sys.stderr)
        for r in doc["refused"]:
            print(f"    REFUSED {r}", file=sys.stderr)
        by_path = {d["path"]: d["summary"] for d in doc["drift"]}
        for p in doc["adopted"]:
            print(f"    ADOPTED {p}:\n{by_path[p]}")
        bad = failed or doc["refused"] or doc["tree_touched"] or not doc["cases"]
        print(
            f"check_emitters_run --apply: {len(doc['adopted'])} of {len(doc['drift'])} drifted "
            f"tracked file(s) adopted; {len(doc['cases']) - len(failed)} emitter(s) ran, "
            f"{len(failed)} failed; review with git diff, then re-run without --apply to confirm 0 drift",
            file=sys.stderr if bad else sys.stdout,
        )
        return 1 if bad else 0
    if "--list" in argv:
        for i, (m, why) in enumerate(ORDER, 1):
            print(f"{i}. {m}\t{why}")
        for m, (need, why) in EXTERNAL.items():
            print(f"-  {m}\tneeds {need} — {why}")
        return 0
    doc = measure()
    if "--json" in argv:
        print(json.dumps(doc, indent=1))
        return 0
    cases = doc["cases"]
    failed = [c for c in cases if c["rc"] != 0]
    total = len(ORDER) + len(EXTERNAL)
    for c in failed:
        print(f"    FAILED {c['module']}: {c['detail']}", file=sys.stderr)
    for d in doc["drift"]:
        print(f"    DRIFT {d['path']}:\n{d['summary']}", file=sys.stderr)
    for p in doc["tree_touched"]:
        print(f"    TREE WRITTEN {p}", file=sys.stderr)
    bad = failed or doc["drift"] or doc["tree_touched"] or not cases
    note = "".join(
        f"\n    SKIP {w['module']} — {w['withheld']}" for w in doc["withheld"]
    )
    print(
        f"check_emitters_run: {len(cases) - len(failed)} ran, {len(failed)} failed, "
        f"{len(doc['withheld'])} skipped of {total}; {len(doc['drift'])} drifted of "
        f"{doc['tracked']} tracked file(s); {len(doc['tree_touched'])} tree file(s) written; "
        f"{doc['untracked_emitted']} untracked output(s) not compared{note}",
        file=sys.stderr if bad else sys.stdout,
    )
    return 1 if bad else 0


def _selftest():
    """The comparison SEES: a drifted emitted file, and a write into the real tree.
    Run over a tiny git repo with one stub emitter, so it costs no palette solve."""
    ok = True

    def see(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        ok = ok and cond

    see(
        "order is non-empty and make_schemes runs first",
        bool(ORDER) and ORDER[0][0] == "make_schemes",
    )
    stale = [m for m, _ in ORDER if not os.path.exists(os.path.join(ROOT, m + ".py"))]
    see(f"no module in the order is missing ({stale})", stale == [])
    with tempfile.TemporaryDirectory() as repo:
        stub = (
            "import os\nhere = os.path.dirname(os.path.abspath(__file__))\n"
            'open(os.path.join(here, "out.colors"), "w").write("A=1\\n")\n'
        )
        for name, body in (("make_stub.py", stub), ("out.colors", "A=1\n")):
            with open(
                os.path.join(repo, name), "w"
            ) as fh:  # atomic-write: exempt — selftest fixture
                fh.write(body)
        subprocess.run(["git", "-C", repo, "init", "-q"], check=True)
        subprocess.run(["git", "-C", repo, "add", "."], check=True)
        order = (("make_stub", "stub"),)
        clean = measure(repo, order, {})
        see(
            "a faithful emitter: ran, no drift, tree untouched",
            clean["cases"][0]["rc"] == 0
            and not clean["drift"]
            and not clean["tree_touched"],
        )

        def drifted(copy):
            with open(
                os.path.join(copy, "out.colors"), "w"
            ) as fh:  # atomic-write: exempt — selftest, private copy
                fh.write("A=2\n")

        d = measure(repo, order, {}, mutate=drifted)
        see(
            "a drifted output is SEEN, with a diff summary",
            [x["path"] for x in d["drift"]] == ["out.colors"]
            and "+A=2" in d["drift"][0]["summary"],
        )

        def write_tree(_copy):
            with open(
                os.path.join(repo, "out.colors"), "w"
            ) as fh:  # atomic-write: exempt — selftest writes its own fixture repo
                fh.write("A=1\n")

        t = measure(repo, order, {}, mutate=write_tree)
        see(
            "a same-bytes write into the REAL tree is SEEN",
            t["tree_touched"] == ["out.colors"],
        )
        # --apply: refuses when an emitter FAILED (nothing adopted, file untouched) ...
        with open(
            os.path.join(repo, "make_bad.py"), "w"
        ) as fh:  # atomic-write: exempt — selftest fixture
            fh.write("import sys\nsys.exit(1)\n")
        subprocess.run(["git", "-C", repo, "add", "make_bad.py"], check=True)
        bad = measure(repo, (("make_bad", "bad"),), {}, mutate=drifted, adopt=True)
        with open(os.path.join(repo, "out.colors")) as fh:
            colors_after_bad = fh.read()
        see(
            "--apply adopts NOTHING when an emitter failed, and says so",
            bad["adopted"] == []
            and bool(bad["refused"])
            and colors_after_bad == "A=1\n",
        )
        # ... and adopts a drifted tracked file when every emitter ran, without calling it a tree write
        ap = measure(repo, order, {}, mutate=drifted, adopt=True)
        with open(os.path.join(repo, "out.colors")) as fh:
            colors_after_ap = fh.read()
        see(
            "--apply adopts the drifted file into the real tree, listed, not a tree write",
            ap["adopted"] == ["out.colors"]
            and not ap["refused"]
            and not ap["tree_touched"]
            and colors_after_ap == "A=2\n",
        )
    print("check_emitters_run selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
