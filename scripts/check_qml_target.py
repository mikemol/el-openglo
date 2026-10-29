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

import grp
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PIN_FILE = os.path.join(ROOT, "catalog", "luthen_pin.json")
HEX = set("0123456789abcdef")


def read_pin(path=PIN_FILE):
    """(pin, None) with the repo name, the 40-hex sha and the paths, or (None, why) when it cannot be read.

    ⚑ THE RUNNER IS READ AT A RECORDED COMMIT, NEVER FROM LUTHEN'S WORKING TREE (mtools:W797, rosettapkg:W121,
    github-8f 2026-10-18): a gate that executes whatever luthen has checked out lets luthen's uncommitted edits
    change this repo's verdict. The pin names the commit and the paths of luthen the runner needs."""
    try:
        with open(path, encoding="utf-8") as fh:
            pin = json.load(fh)
    except (OSError, ValueError) as err:
        return None, f"{os.path.relpath(path, ROOT)} is unreadable: {err}"
    sha = pin.get("sha") if isinstance(pin, dict) else None
    paths = pin.get("paths") if isinstance(pin, dict) else None
    if not (isinstance(sha, str) and len(sha) == 40 and set(sha) <= HEX):
        return None, "the luthen pin has no 40-hex sha"
    if not (
        isinstance(paths, list) and paths and all(isinstance(p, str) for p in paths)
    ):
        return None, "the luthen pin lists no paths"
    return pin, None


def object_stores(root=ROOT, environ=None):
    """Where a git repository holding luthen's objects may be, in order: LUTHEN_OBSERVABILITY, the sibling of
    this checkout, then ~/github. Only its OBJECT DATABASE is read (`git archive <sha>`), so which working tree
    it has checked out, and what is uncommitted in it, cannot reach the verdict."""
    env = os.environ if environ is None else environ
    return [
        c
        for c in (
            env.get("LUTHEN_OBSERVABILITY"),
            os.path.join(os.path.dirname(root), "luthen-observability"),
            os.path.expanduser("~/github/luthen-observability"),
        )
        if c
    ]


def materialize(pin, dest, stores=None):
    """(dest, None) after the pinned paths are extracted at the pinned sha into `dest`, else (None, why)."""
    tried = object_stores() if stores is None else stores
    for store in tried:
        argv = ["git", "-c", "safe.directory=*", "-C", store, "archive"]
        r = subprocess.run(
            [*argv, "--format=tar", pin["sha"], *pin["paths"]],
            capture_output=True,
            check=False,
        )
        if r.returncode != 0:
            continue
        with tarfile.open(fileobj=io.BytesIO(r.stdout)) as tar:
            tar.extractall(dest, filter="data")
        return dest, None
    return None, (
        f"commit {pin['sha'][:12]} of luthen is in none of: "
        + ", ".join(tried)
        + " (set LUTHEN_OBSERVABILITY to a clone that holds it)"
    )


# (kind, glob relative to <stage>/usr/share, entry file name)
ENTRIES = (
    ("plasmoid", "plasma/plasmoids", "contents/ui/main.qml"),
    ("wallpaper", "plasma/wallpapers", "contents/ui/main.qml"),
    ("tabbox", "kwin/tabbox", "contents/ui/main.qml"),
    ("sddm", "sddm/themes", "Main.qml"),
    ("splash", "plasma/look-and-feel", "contents/splash/Splash.qml"),
)


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


def in_group(name):
    """True when this process already holds the group `name` (a supplementary group of the session)."""
    try:
        return grp.getgrnam(name).gr_gid in os.getgroups()
    except KeyError:
        return False


def runner_unavailable():
    """None when luthen's runner can be invoked here, else the reason it cannot.

    ⚑ `sg k3s` IS ONLY FOR A SESSION THAT DOES NOT YET HOLD THE GROUP (measured 2026-10-18): a session started
    after the user joined k3s already has it (`id` lists 998(k3s)), and runs the runner directly. `sg` is
    newgrp, a setuid binary, and under no_new_privs (the agent's shell has NoNewPrivs 1) the setuid bit is
    ignored, so it fails with `setgroups: Operation not permitted`, a fact about the wrapper and not about k3s.
    """
    if not in_group("k3s") and not shutil.which("sg"):
        return "sg is not installed (the k3s group runner needs it)"
    return None


HOSTS = {"tabbox": "kwin-tabbox"}


def host_of(kind):
    """The KDE host luthen loads a package kind under: KWin's own org.kde.kwin module is registered
    in-process by kwin-tabbox-preview, so a switcher loads there; every other kind needs none."""
    return HOSTS.get(kind, "none")


def command(src, entry, out, host, luthen):
    """The shell line that runs luthen checks.qml_check on one directory, from the pinned copy `luthen`."""
    return (
        f"cd {luthen} && python3 -m checks.qml_check --src {src} --entry {entry} "
        f"--out {out} --host {host}"
    )


def run_check(src, entry, out, host, luthen):
    """luthen checks.qml_check on one directory: (verdict dict, exit code)."""
    cmd = command(src, entry, out, host, luthen)
    argv = ["bash", "-c", cmd] if in_group("k3s") else ["sg", "k3s", "-c", cmd]
    r = subprocess.run(argv, capture_output=True, text=True, check=False)
    line = next(
        (ln for ln in reversed(r.stdout.splitlines()) if ln.startswith("{")), None
    )
    try:
        verdict = json.loads(line) if line else {}
    except ValueError:
        verdict = {}
    return verdict, r.returncode, (r.stderr or r.stdout)[-300:]


# The runner exits that mean "it could not evaluate": a fact about the machine, never a verdict (W764).
# 7 is CANNOT_RUN in the fleet exit table (mtools corpus/exit-table.json). luthen-observability's qml_check
# emitted 2 (USAGE/BLOCK in that table) until luthen-observability:W1714 (85603ff1) moved every cannot-run
# path to 7; this reads the pin that carries it (catalog/luthen_pin.json), so 2 is dropped (W769). An exit 2
# with a verdict is now a RESULT, and one with none is still withheld by runner_withheld's empty-verdict rule.
RUNNER_CANNOT_RUN = (7,)


def timing_report(timings, n_cases):
    """One line saying where a run's wall went: the staging, then the qml_check runs (W783).

    `timings` is measure's list of (what, seconds); n_cases is how many cases it measured, so the
    count of runs is read as `n of m` and a case sharing a tree digest shows as not run."""
    stage_s = sum(s for what, s in timings if what == "stage")
    built = sorted(((s, what) for what, s in timings if what != "stage"), reverse=True)
    total = sum(s for s, _ in built)
    median = built[len(built) // 2][0] if built else 0.0
    slow = ", ".join(f"{what} {s:.1f} s" for s, what in built[:3]) or "none"
    return (
        f"check_qml_target: stage {stage_s:.1f} s; {len(built)} of {n_cases} case(s) ran a "
        f"qml_check ({n_cases - len(built)} share a tree digest); qml_check total {total:.1f} s, "
        f"median {median:.1f} s; slowest: {slow}"
    )


def runner_withheld(rc, verdict):
    """True when the runner's exit code `rc` (or an empty `verdict`) says it could not run."""
    return rc in RUNNER_CANNOT_RUN or not verdict


def measure(stage_dir=None, timings=None):
    """The cases. `timings`, a list, collects (what, seconds): ("stage", s) for the staging and
    (package, s) for each qml_check actually RUN (a case sharing a tree digest runs none), so one
    run says where its wall goes (W783)."""
    import time

    cases = []
    with tempfile.TemporaryDirectory() as td:
        sd = stage_dir
        if stage_dir is None:
            # W788: the staged tree is SHARED (one per tree digest, staged once under a lock), where
            # it was a private 40 s make_deb --stage per run; it is frozen, and this check only reads it
            import staging_cache

            started = time.monotonic()
            sd = staging_cache.shared_stage()
            if timings is not None:
                timings.append(("stage", time.monotonic() - started))
        why = runner_unavailable()
        luthen = None
        if not why:
            pin, why = read_pin()
            if pin:
                luthen, why = materialize(pin, os.path.join(td, "luthen"))
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
                out = os.path.join(td, "out-" + pkg)
                started = time.monotonic()
                verdict, rc, tail = run_check(d, entry, out, host_of(kind), luthen)
                if timings is not None:
                    timings.append((pkg, time.monotonic() - started))
                if runner_withheld(rc, verdict):
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

    def chk(label: str, got: object, want: object) -> None:
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    chk(
        "a tabbox loads under luthen's kwin-tabbox host, every other kind under none",
        [host_of(k) for k, _s, _e in ENTRIES],
        ["none", "none", "kwin-tabbox", "none", "none"],
    )
    chk(
        "the runner line carries the host and runs from the pinned copy",
        command("/s", "main.qml", "/o", "kwin-tabbox", "/l").startswith("cd /l && ")
        and command("/s", "main.qml", "/o", "kwin-tabbox", "/l").endswith(
            "--host kwin-tabbox"
        ),
        True,
    )
    with tempfile.TemporaryDirectory() as td:
        pin_file = os.path.join(td, "pin.json")
        for label, text in (
            ("a pin that is not JSON", "{"),
            ("a pin whose sha is not 40 hex", '{"sha": "abc", "paths": ["a"]}'),
            ("a pin that lists no paths", f'{{"sha": "{"a" * 40}", "paths": []}}'),
        ):
            with open(pin_file, "w", encoding="utf-8") as fh:
                fh.write(text)
            chk(f"read_pin refuses {label}", read_pin(pin_file)[0], None)
        chk("read_pin reads the real pin", read_pin()[0] is not None, True)
        repo = os.path.join(td, "luthen")
        os.makedirs(os.path.join(repo, "checks"))
        gitc = ["git", "-C", repo, "-c", "user.name=t", "-c", "user.email=t@t"]
        runner = os.path.join(repo, "checks", "qml_check.py")
        subprocess.run(["git", "-C", repo, "init", "-q"], check=True)
        with open(runner, "w", encoding="utf-8") as fh:
            fh.write("COMMITTED\n")
        subprocess.run([*gitc, "add", "checks"], check=True)
        subprocess.run([*gitc, "commit", "-q", "-m", "c"], check=True)
        sha = subprocess.run(
            [*gitc, "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
        with open(runner, "w", encoding="utf-8") as fh:
            fh.write("UNCOMMITTED EDIT\n")
        out = os.path.join(td, "out")
        got, _why = materialize({"sha": sha, "paths": ["checks"]}, out, [repo])
        with open(os.path.join(out, "checks", "qml_check.py"), encoding="utf-8") as fh:
            copied = fh.read()
        chk(
            "materialize reads the pinned commit, not the working tree's uncommitted edit",
            (got, copied),
            (out, "COMMITTED\n"),
        )
        missing = materialize({"sha": "0" * 40, "paths": ["checks"]}, out, [repo])
        chk(
            "a sha no store holds is None and names the commit and every store tried",
            (missing[0], "000000000000" in missing[1], repo in missing[1]),
            (None, True, True),
        )
        chk(
            "object_stores: the env var first, then the sibling, then ~/github",
            object_stores("/a/b/el", {"LUTHEN_OBSERVABILITY": "/x/l"}),
            [
                "/x/l",
                "/a/b/luthen-observability",
                os.path.expanduser("~/github/luthen-observability"),
            ],
        )
    held = grp.getgrgid(os.getgroups()[0]).gr_name if os.getgroups() else None
    chk(
        "in_group is true for a group the process holds and false for one that is not there",
        (held is None or in_group(held), in_group("no-such-group-zz9")),
        (True, False),
    )
    # W764, W769: the runner's "could not run" exit is the fleet code 7 alone (luthen-observability:W1714
    # moved qml_check off 2); a refused QML verdict at exit 1 or a verdict at exit 2 and a clean one at 0
    # stay results, and no verdict at all is withheld whatever the exit.
    refused = {"state": "refused", "step": "lint"}
    chk(
        "exit 7 is withheld, 2 with a verdict is a result now (W769), 1 and 0 are results, no verdict is withheld",
        [
            runner_withheld(7, {}),
            runner_withheld(2, refused),
            runner_withheld(1, refused),
            runner_withheld(0, {"state": "ok"}),
            runner_withheld(1, {}),
        ],
        [True, False, False, False, True],
    )
    chk(
        "timing_report reads n of m: 2 qml_check runs for 5 cases, 3 sharing a digest, the slowest first",
        timing_report([("stage", 25.0), ("a", 4.0), ("b", 9.0)], 5),
        "check_qml_target: stage 25.0 s; 2 of 5 case(s) ran a qml_check (3 share a tree digest); "
        "qml_check total 13.0 s, median 4.0 s; slowest: b 9.0 s, a 4.0 s",
    )
    chk(
        "timing_report with no run says none, not a division",
        timing_report([("stage", 1.0)], 0).endswith("slowest: none"),
        True,
    )
    why = runner_unavailable()
    if why:
        print(f"  SKIP the runner cannot run here: {why}")
        print(f"check_qml_target selftest: {'PASS' if ok else 'FAIL'} (1 skip(s))")
        return ok
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
        pinned, _why = materialize(read_pin()[0], os.path.join(td, "pinned"))
        v, rc, tail = run_check(
            clean, "main.qml", os.path.join(td, "o1"), "none", pinned
        )
        if not v:
            # ⚑ NO VERDICT AT ALL IS "COULD NOT MEASURE", as `measure` already reads it
            # (W454, 2026-10-10: after the host reboot k3s was not up, the runner printed
            # no verdict, and this selftest FAILED the gate for a fact about the machine).
            print(f"  SKIP the runner produced no verdict (exit {rc}): {tail}")
            print(f"check_qml_target selftest: {'PASS' if ok else 'FAIL'} (1 skip(s))")
            return ok
        chk(
            "a clean document is ok under the target Qt",
            (rc, v.get("state")),
            (0, "ok"),
        )
        v, rc, _ = run_check(bad, "main.qml", os.path.join(td, "o2"), "none", pinned)
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
    known = {"--json", "--list", "--selftest", "--timing"}
    stage_dir = None
    args = argv[1:]
    seen = []
    i = 0
    while i < len(args):
        if args[i] == "--stage":
            if i + 1 >= len(args) or not os.path.isdir(args[i + 1]):
                print(
                    "check_qml_target: --stage needs an existing directory",
                    file=sys.stderr,
                )
                return 2
            stage_dir = args[i + 1]
            i += 2
            continue
        if args[i] not in known:
            print(f"check_qml_target: unknown flag {args[i]!r}", file=sys.stderr)
            return 2
        seen.append(args[i])
        i += 1
    if "--selftest" in seen:
        return 0 if _selftest() else 1
    timings = [] if "--timing" in seen else None
    doc = measure(stage_dir, timings=timings)
    if timings is not None:
        print(timing_report(timings, len(doc["cases"])))
        return 0 if doc["cases"] else 1
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
