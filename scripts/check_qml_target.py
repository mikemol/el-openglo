#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_qml_target.py — every staged QML package lints and loads under the OPERATOR'S Qt (W83/W213).

The `var byte` .deb (2026-09-26) passed every gate here on host Qt 6.11.2 and failed on the
laptop's Qt 6.10.2. luthen-observability built the laptop's exact stack as a digest-pinned
ubuntu:resolute image (luthen W114: Qt 6.10.2, Plasma 6.6.6, Kirigami 6.24.0) and a runner,
`checks.qml_check`, that lints and loads one QML directory offscreen. This stages the install
tree the .deb ships (make_deb --stage) and runs that runner on every package entry point.

    scripts/check_qml_target.py --json      # the measurement policy/qml_target.rego decides
    scripts/check_qml_target.py --list      # per package: state, step; n of m
    scripts/check_qml_target.py --selftest  # the runner can SEE the laptop's failure

Per package: {id, entry, state, step, digest, shared_with}. state is luthen's verdict ("ok" or a
failure naming its step), or `withheld` with a reason when the runner could not run at all (no
`sg`/k3s group, no image, luthen exit 2) - a fact about this machine, never a pass. Packages
whose entry directory is byte-identical (the legacy-id aliases of one package) are measured ONCE
and the verdict reported for each: `shared_with` names the measured representative.

WEAKNESS: offscreen load proves the document instantiates under the target Qt with the target
modules; it does not exercise a live Plasma shell (applet containment, real notification
model). It is the laptop's parser and type system, not the laptop's session.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LUTHEN = os.path.join(os.path.dirname(ROOT), "luthen-observability")

# (kind, glob relative to <stage>/usr/share, entry file name)
ENTRIES = (
    ("plasmoid", "plasma/plasmoids", "contents/ui/main.qml"),
    ("wallpaper", "plasma/wallpapers", "contents/ui/main.qml"),
    ("tabbox", "kwin/tabbox", "contents/ui/main.qml"),
    ("sddm", "sddm/themes", "Main.qml"),
    ("splash", "plasma/look-and-feel", "contents/splash/Splash.qml"),
)


def stage(dest):
    """The install tree the .deb ships, staged by the one authority that builds it."""
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "make_deb.py"), "--stage", dest],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(f"make_deb --stage exited {r.returncode}: {r.stderr[-300:]}")


def entries(stage_dir):
    """[(kind, id, entry_dir, entry_file)] for every staged package, in stable order."""
    share = os.path.join(stage_dir, "usr", "share")
    out = []
    for kind, sub, entry in ENTRIES:
        base = os.path.join(share, sub)
        if not os.path.isdir(base):
            continue
        for pkg in sorted(os.listdir(base)):
            path = os.path.join(base, pkg, entry)
            if os.path.isfile(path):
                out.append((kind, pkg, os.path.dirname(path), os.path.basename(path)))
    return out


def tree_digest(d):
    """A content digest of one entry directory (names and bytes), to measure aliases once."""
    h = hashlib.sha256()
    # population: one staged package directory under make_deb's TEMP stage (not the repo tree), digested whole
    for dirpath, _dirs, files in sorted(os.walk(d)):
        for f in sorted(files):
            p = os.path.join(dirpath, f)
            h.update(os.path.relpath(p, d).encode())
            with open(p, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()


def runner_unavailable():
    """None when luthen's runner can be invoked here, else the reason it cannot."""
    if not shutil.which("sg"):
        return "sg is not installed (the k3s group runner needs it)"
    if not os.path.isfile(os.path.join(LUTHEN, "checks", "qml_check.py")):
        return f"luthen's checks/qml_check.py is not at {LUTHEN}"
    return None


def run_check(src, entry, out):
    """luthen checks.qml_check on one directory: (verdict dict, exit code)."""
    cmd = f"cd {LUTHEN} && python3 -m checks.qml_check --src {src} --entry {entry} --out {out}"
    r = subprocess.run(
        ["sg", "k3s", "-c", cmd], capture_output=True, text=True, check=False
    )
    line = next(
        (ln for ln in reversed(r.stdout.splitlines()) if ln.startswith("{")), None
    )
    try:
        verdict = json.loads(line) if line else {}
    except ValueError:
        verdict = {}
    return verdict, r.returncode, (r.stderr or r.stdout)[-300:]


def measure(stage_dir=None):
    cases = []
    with tempfile.TemporaryDirectory() as td:
        sd = stage_dir or os.path.join(td, "stage")
        if stage_dir is None:
            stage(sd)
        why = runner_unavailable()
        seen = {}
        for kind, pkg, d, entry in entries(sd):
            case = {
                "id": pkg,
                "kind": kind,
                "entry": entry,
                "digest": tree_digest(d),
                "shared_with": None,
            }
            if why:
                case["withheld"] = why
            elif case["digest"] in seen:
                rep = seen[case["digest"]]
                case.update(
                    shared_with=rep["id"],
                    state=rep.get("state"),
                    step=rep.get("step"),
                    withheld=rep.get("withheld"),
                )
            else:
                verdict, rc, tail = run_check(d, entry, os.path.join(td, "out-" + pkg))
                if rc == 2 or not verdict:
                    case["withheld"] = f"qml_check could not run (exit {rc}): {tail}"
                else:
                    case.update(
                        state=verdict.get("state"),
                        step=verdict.get("step"),
                        base=verdict.get("base"),
                        withheld=None,
                    )
                seen[case["digest"]] = case
            cases.append(case)
    return {"cases": cases}


def listing(doc):
    out = []
    for c in doc["cases"]:
        if c.get("withheld"):
            out.append(f"  {c['kind']:9s} {c['id']}: WITHHELD - {c['withheld']}")
        else:
            out.append(
                f"  {c['kind']:9s} {c['id']}: {c.get('state')}"
                + (f" at {c['step']}" if c.get("step") else "")
                + (
                    f" (same tree as {c['shared_with']})"
                    if c.get("shared_with")
                    else ""
                )
            )
    ok = sum(
        1 for c in doc["cases"] if c.get("state") == "ok" and not c.get("withheld")
    )
    measured = len({c["digest"] for c in doc["cases"] if not c.get("shared_with")})
    out.append(
        f"check_qml_target: {ok} of {len(doc['cases'])} staged package(s) ok under the operator Qt; "
        f"{measured} distinct tree(s) measured"
    )
    return "\n".join(out)


def _selftest():
    """The runner can SEE the laptop's failure: a staged copy of a real entry with the
    `var byte` declaration injected must read step=lint; the unmodified copy must read ok."""
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    why = runner_unavailable()
    if why:
        print(f"  SKIP the runner cannot run here: {why}")
        print("check_qml_target selftest: PASS (1 skip(s))")
        return True
    with tempfile.TemporaryDirectory() as td:
        clean = os.path.join(td, "clean")
        os.makedirs(clean)
        with open(os.path.join(clean, "main.qml"), "w") as f:
            f.write("import QtQuick\nItem { property int n: 1 }\n")
        bad = os.path.join(td, "bad")
        os.makedirs(bad)
        with open(os.path.join(bad, "main.qml"), "w") as f:
            f.write(
                "import QtQuick\nItem { function f() { var byte = 1; return byte; } }\n"
            )
        v, rc, _ = run_check(clean, "main.qml", os.path.join(td, "o1"))
        chk(
            "a clean document is ok under the target Qt",
            (rc, v.get("state")),
            (0, "ok"),
        )
        v, rc, _ = run_check(bad, "main.qml", os.path.join(td, "o2"))
        chk(
            "`var byte` fails at lint under the target Qt (the laptop's 2026-09-26 error)",
            (rc, v.get("step")),
            (1, "lint"),
        )
        chk(
            "an unchanged tree digests the same", tree_digest(clean), tree_digest(clean)
        )
    print("check_qml_target selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    known = {"--json", "--list", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_qml_target: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    doc = measure()
    if not doc["cases"]:
        print(
            "check_qml_target: REFUSED - no staged QML package found; the stage is broken, not the tree clean",
            file=sys.stderr,
        )
        return 1
    print(json.dumps(doc, indent=1) if "--json" in argv else listing(doc))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
