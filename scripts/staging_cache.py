#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""staging_cache.py — one shared staged install tree per tree digest (W787 under W786).

⚑ WHY. `make_deb --stage` is about 40 s of CPU every time (measured 2026-10-29: 45.9 s and 39.7 s for
two runs back to back; the page cache saves only about 6 s), and three checks each run it for the SAME
tree: check_qml_target, check_package_load and check_plugin_ids. Under the gate's load that is three
stagings contending with everything else, and the 600 s wall backstop is what refused the stacks of
W754 to W777. Two stagings of the same tree differ in exactly four files (the TTFs); the rest is
byte-identical, so one tree can serve every consumer.

    scripts/staging_cache.py --key       # the tree digest a staging would be filed under
    scripts/staging_cache.py --selftest

THE KEY is the sha256 over (path, bytes) of every file git_tracked.files() names, plus the Python
version. It is SOUND by construction: any tracked edit changes it, so it can over-invalidate and never
serve a stale tree; uv.lock is tracked, so the dependency versions ride in it. THE LOCATION is a
directory under the temp dir (a bazel test has its own, removed with the test), `stage-<key16>`, with a
lock file beside it: the first claim stages into a private `.part-*` directory under the exclusive
flock and renames it into place, the rest wait on the lock and reuse. The shared tree is FROZEN (write
bits off), so a consumer that writes into it fails loudly instead of silently changing what the others
read. Each stage PRUNES to the newest KEEP trees: a cache keyed per tree grows with every edit, which
is the leak W784 removed from /var/tmp.

⚑ WEAKNESS, STATED. Untracked inputs are not in the key: the gitignored palette cache only speeds the
solve (the palette is deterministic), and an environment variable make_deb reads would not be seen. A
consumer holding an OLDER tree open while two newer ones are staged loses it to the prune; edits do not
happen mid-gate, so this does not arise there. The four TTFs differ run to run, so a tree is shared,
never re-derived.
"""

import fcntl
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

PREFIX = "stage-"
PART = ".part-"
KEEP = 2


def tree_key(root=ROOT, files=None):
    """The sha256 hex digest of the tracked tree at `root` plus the Python version.

    `files` overrides the population (relative paths), for the selftest; by default every file
    git_tracked.files names. A symlink contributes its target text, a directory nothing."""
    import git_tracked

    names = files if files is not None else git_tracked.files(root=root)
    h = hashlib.sha256()
    h.update(sys.version.encode())
    for name in sorted(names):
        path = os.path.join(root, name)
        h.update(b"\0" + name.encode() + b"\0")
        if os.path.islink(path):
            h.update(os.readlink(path).encode())
        elif os.path.isfile(path):
            with open(path, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()


def parent_dir():
    """Where the shared trees live: a directory under the temp dir."""
    return os.path.join(tempfile.gettempdir(), "el-openglo-stage")


def make_deb_stage(dest, root=ROOT):
    """Stage the install tree into `dest` with the one authority that builds it."""
    r = subprocess.run(
        [sys.executable, os.path.join(root, "make_deb.py"), "--stage", dest],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        raise RuntimeError(f"make_deb --stage exited {r.returncode}: {r.stderr[-300:]}")


def _remove(path):
    """rmtree a frozen tree: give the directories their write bit back first."""
    # population: this cache's own staged tree under the temp dir, not the repo
    for dp, dirs, _files in os.walk(path):
        os.chmod(dp, 0o755)
        for d in dirs:
            os.chmod(os.path.join(dp, d), 0o755)
    shutil.rmtree(path, ignore_errors=True)


def _freeze(path):
    """Drop every write bit under `path`: a consumer that writes into a shared tree must fail."""
    # population: this cache's own staged tree under the temp dir, not the repo
    for dp, _dirs, files in os.walk(path, topdown=False):
        for name in files:
            full = os.path.join(dp, name)
            if not os.path.islink(full):
                os.chmod(full, os.stat(full).st_mode & ~0o222)
        os.chmod(dp, os.stat(dp).st_mode & ~0o222)


def prune(parent, keep=KEEP):
    """Remove dead `.part-*` leftovers and all but the newest `keep` shared trees.

    Called with the exclusive lock held, so no live staging owns a `.part-*` directory."""
    for name in os.listdir(parent):
        if name.startswith(PART):
            _remove(os.path.join(parent, name))
    trees = sorted(
        (n for n in os.listdir(parent) if n.startswith(PREFIX)),
        key=lambda n: os.stat(os.path.join(parent, n)).st_mtime,
        reverse=True,
    )
    for name in trees[keep:]:
        _remove(os.path.join(parent, name))


def shared_stage(root=ROOT, parent=None, stager=None, key=None, keep=KEEP):
    """The path of the shared staged tree for this tree digest, staging it at most once.

    `stager(dest)` fills a directory (default make_deb --stage); a stager that raises leaves nothing
    behind and the next caller retries. Waiting callers hold no CPU: they block on the flock."""
    parent = parent or parent_dir()
    os.makedirs(parent, exist_ok=True)
    key = key or tree_key(root)
    final = os.path.join(parent, PREFIX + key[:16])
    with open(os.path.join(parent, ".lock"), "a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        prune(parent, keep)
        if not os.path.isdir(final):
            part = tempfile.mkdtemp(prefix=PART, dir=parent)
            try:
                (stager or (lambda d: make_deb_stage(d, root)))(part)
                _freeze(part)
                os.rename(part, final)
            except BaseException:
                _remove(part)
                raise
        os.utime(final)
        prune(parent, keep)
    return final


def main(argv):
    args = argv[1:]
    for a in args:
        if a not in ("--key", "--selftest"):
            print(f"staging_cache: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in args:
        return 0 if _selftest() else 1
    if "--key" in args:
        print(tree_key())
        return 0
    print("staging_cache: needs --key or --selftest", file=sys.stderr)
    return 2


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    with tempfile.TemporaryDirectory() as td:
        tree = os.path.join(td, "tree")
        os.makedirs(tree)
        for name, body in (("a.txt", b"one"), ("b.txt", b"two")):
            with open(os.path.join(tree, name), "wb") as fh:
                fh.write(body)
        k1 = tree_key(tree, ["a.txt", "b.txt"])
        chk(
            "the key is stable, order-free and 64 hex",
            (k1 == tree_key(tree, ["b.txt", "a.txt"]), len(k1)),
            (True, 64),
        )
        with open(os.path.join(tree, "b.txt"), "wb") as fh:
            fh.write(b"twp")
        chk(
            "one changed byte changes the key",
            tree_key(tree, ["a.txt", "b.txt"]) != k1,
            True,
        )

        parent = os.path.join(td, "cache")
        calls = []

        def stager(dest):
            calls.append(dest)
            time.sleep(0.2)
            with open(os.path.join(dest, "marker"), "w", encoding="utf-8") as fh:
                fh.write("staged")

        got = []
        threads = [
            threading.Thread(
                target=lambda: got.append(
                    shared_stage(parent=parent, stager=stager, key="a" * 64)
                )
            )
            for _ in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        chk(
            "four racing callers stage ONCE and all get the same tree",
            (len(calls), len(set(got))),
            (1, 1),
        )
        again = shared_stage(parent=parent, stager=stager, key="a" * 64)
        chk(
            "a later call reuses it without staging",
            (again == got[0], len(calls)),
            (True, 1),
        )
        try:
            with open(os.path.join(got[0], "marker"), "w", encoding="utf-8") as fh:
                fh.write("x")
            wrote = True
        except PermissionError:
            wrote = False
        chk("the shared tree is frozen: a write into it fails", wrote, False)

        def failing(dest):
            raise RuntimeError("boom")

        try:
            shared_stage(parent=parent, stager=failing, key="b" * 64)
            raised = False
        except RuntimeError:
            raised = True
        left = [n for n in os.listdir(parent) if n.startswith((PART, PREFIX + "b"))]
        chk(
            "a failing stager raises and leaves no partial tree",
            (raised, left),
            (True, []),
        )
        retry = shared_stage(parent=parent, stager=stager, key="b" * 64)
        chk("...and the next caller retries and succeeds", os.path.isdir(retry), True)
        for ch in "cde":
            time.sleep(0.02)
            shared_stage(parent=parent, stager=stager, key=ch * 64)
        trees = sorted(n for n in os.listdir(parent) if n.startswith(PREFIX))
        chk(
            "each stage prunes to the newest two trees",
            trees,
            [PREFIX + "d" * 16, PREFIX + "e" * 16],
        )
    real = tree_key()
    chk("the real tree has a stable key", real == tree_key() and len(real) == 64, True)
    print("staging_cache selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv))
