#!/usr/bin/env python3
"""schemes_artifact.py — the `schemes` action's OUTPUT as one content-addressed artifact (W75).

⚑ WHY (operator, 2026-09-23: "that's why all that shit needs to be passed as build
artifacts"). W68 stopped every gated check from WRITING the tree, and atomic_write
stopped a reader seeing HALF a file. Neither says WHICH version a reader sees: ~20
readers opened the tracked EL-*.colors by path (make_preview.parse_scheme), so two
checks in one gate run could judge two different palettes if anything — an operator's
`make_schemes.py`, another session, a checkout — moved the working tree between them.
Ordering was a property of TIMING, and a race is fixed by construction or not at all.

So the colours are a declared build OUTPUT, and a reader declares them as an INPUT:

  · `materialise()` copies the schemes action's outputs (every `*.colors` at the root,
    the roster check_action_key.ACTIONS declares for "schemes") into
    `.build/schemes/<digest>/`, read-only, renamed into place whole. The digest is over
    (name, sha256(bytes)) of every member, so the directory NAME is its content.
  · The gate (scripts/worklist_gate.py) materialises ONCE, before any check runs, and
    hands the path down as `schemes=<dir>` in PAPERKIT_BUILT_ARTIFACTS — paperkit's own
    `builds` protocol (tools/cell.bzl cell_builds_env), so a Bazel cell that declares
    the artifact hands a reader the same variable this does.
  · `directory()` is what every reader asks. Declared: that directory, its digest
    RE-VERIFIED against its name (a tampered or half-written snapshot is refused, not
    read). Undeclared (a check run by hand): the reader materialises its OWN snapshot,
    once per process — so even outside the gate a process sees exactly one version.

    schemes_artifact.py --materialise   # snapshot the tree's schemes; print `<digest> <dir>`
    schemes_artifact.py --where         # what THIS process would read, and why
    schemes_artifact.py --json          # the measurement: digest, members, source
    schemes_artifact.py --json --parsed # ...plus a digest of what parse_scheme returned
    schemes_artifact.py --race          # the ordering, in a scratch copy under a live writer
    schemes_artifact.py --selftest      # a concurrent rewrite cannot reach a snapshot reader

⚑ NO FALLBACK LADDER. paperkit's boundaries_wheel measured the cost of one: a check that
could not tell "I was handed the artifact" from "I walked to the checkout and found one"
passed outside every cell. A DECLARED path that is absent or fails verification RAISES;
only an UNDECLARED run self-materialises, and --where says which happened.

WEAKNESSES, stated. (1) A snapshot is taken FROM the working tree; if a writer rewrites
the tree DURING the copy, the members could straddle two versions. The copy is read
twice and refused unless both reads agree (then retried), which closes the window for
a writer that finishes; a writer rewriting continuously makes this RAISE, never mix.
(2) It fixes WHICH .colors a reader sees; it does not make the reader's OTHER inputs
(templates, make_schemes.GRID from .palette-cache.json, the reader's own code)
content-addressed — those are still read by path, and GRID is the next edge (see
catalog/build-graph.md). (3) Snapshots accumulate under .build/schemes; nothing
collects them (they are ~20 KiB each and content-addressed, so a re-run reuses one).
(4) The digest is a fact about the BYTES, not about whether make_schemes would still
emit them: currency stays check_action_key's question.
"""
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
KEY = "schemes"                              # the artifact's name in PAPERKIT_BUILT_ARTIFACTS
ENV = "PAPERKIT_BUILT_ARTIFACTS"
SUFFIX = ".colors"                           # check_action_key.ACTIONS "schemes": (".", (".colors",))
STORE = os.path.join(ROOT, ".build", "schemes")
STABLE_TRIES = 5

_RESOLVED = {}                               # per-process memo: {"dir", "digest", "how"}


class SnapshotError(RuntimeError):
    """A declared snapshot is absent or does not match its name, or the source never settled."""


def members(src):
    """Sorted member names of the schemes artifact in `src` (files ending .colors)."""
    return sorted(n for n in os.listdir(src)
                  if n.endswith(SUFFIX) and os.path.isfile(os.path.join(src, n)))


def digest(files):
    """sha256 over (name, sha256(bytes)) of {name: bytes}, sorted by name."""
    h = hashlib.sha256()
    for n in sorted(files):
        h.update(n.encode() + b"\0" + hashlib.sha256(files[n]).hexdigest().encode() + b"\0")
    return h.hexdigest()


def _read(src):
    out = {}
    for n in members(src):
        with open(os.path.join(src, n), "rb") as fh:
            out[n] = fh.read()
    return out


def _read_stable(src):
    """{name: bytes} read twice with agreement, or SnapshotError. An empty population refuses."""
    prev = _read(src)
    for _ in range(STABLE_TRIES):
        cur = _read(src)
        if cur == prev:
            if not cur:
                raise SnapshotError(f"no *{SUFFIX} in {src}: an empty artifact is a broken "
                                    f"search, not a clean tree")
            return cur
        prev = cur
    raise SnapshotError(f"{src}'s *{SUFFIX} changed on each of {STABLE_TRIES} reads — a writer "
                        f"is still running; refusing to snapshot a mixture")


def verify(path):
    """The digest of the snapshot at `path`, if it equals the directory's NAME; else raise."""
    if not os.path.isdir(path):
        raise SnapshotError(f"declared {KEY} snapshot {path} does not exist")
    files = _read(path)
    got = digest(files) if files else None
    if got != os.path.basename(os.path.normpath(path)):
        raise SnapshotError(f"{path}: content digest {str(got)[:16]}… does not match its name "
                            f"— a snapshot that is not its own content is not an artifact")
    return got


def materialise(src=ROOT, store=STORE):
    """(digest, dir): `src`'s schemes, frozen into store/<digest>, read-only. Idempotent."""
    files = _read_stable(src)
    d = digest(files)
    dest = os.path.join(store, d)
    if os.path.isdir(dest):
        verify(dest)
        return d, dest
    os.makedirs(store, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix=".tmp-", dir=store)
    try:
        for n, data in files.items():
            p = os.path.join(tmp, n)
            with open(p, "wb") as fh:  # atomic-write: exempt — private temp dir, renamed whole
                fh.write(data)
            os.chmod(p, stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        os.chmod(tmp, 0o755)
        try:
            os.rename(tmp, dest)                 # the whole snapshot appears at once
        except OSError:
            if not os.path.isdir(dest):          # lost a race to an identical snapshot: fine
                raise
    finally:
        if os.path.isdir(tmp):
            shutil.rmtree(tmp, ignore_errors=True)
    verify(dest)
    return d, dest


def declared(environ=None):
    """The `schemes=<dir>` path in PAPERKIT_BUILT_ARTIFACTS, or None."""
    for pair in (environ if environ is not None else os.environ).get(ENV, "").split():
        k, _, v = pair.partition("=")
        if k == KEY:
            return v
    return None


def with_declared(environ, path):
    """A copy of `environ` whose PAPERKIT_BUILT_ARTIFACTS declares `schemes=path`
    (path None: the pair is REMOVED — a private build must read its own outputs)."""
    env = dict(environ)
    pairs = [p for p in env.get(ENV, "").split() if p.partition("=")[0] != KEY]
    if path is not None:
        pairs.append(f"{KEY}={path}")
    if pairs:
        env[ENV] = " ".join(pairs)
    else:
        env.pop(ENV, None)
    return env


def resolve():
    """{"dir", "digest", "how"} — the ONE schemes artifact this process reads."""
    if not _RESOLVED:
        path = declared()
        if path is not None:
            _RESOLVED.update(dir=path, digest=verify(path), how="declared by " + ENV)
        else:
            d, path = materialise()
            _RESOLVED.update(dir=path, digest=d, how="self-materialised (no declared input)")
    return dict(_RESOLVED)


def directory():
    return resolve()["dir"]


def path(variant):
    """The snapshot's `<variant>.colors`."""
    return os.path.join(directory(), variant + SUFFIX)


def variants():
    """The variants the artifact carries — the population, from the snapshot, not the tree."""
    return [n[:-len(SUFFIX)] for n in members(directory())]


def _selftest():
    """The snapshot can SEE: a concurrent rewrite of the source does not reach a reader;
    a tampered snapshot is refused; an empty source refuses; a declared path wins."""
    import subprocess
    ok = True

    def see(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        ok = ok and bool(cond)

    with tempfile.TemporaryDirectory(dir=os.path.join(ROOT, ".build") if os.path.isdir(
            os.path.join(ROOT, ".build")) else None) as td:
        src, store = os.path.join(td, "src"), os.path.join(td, "store")
        os.makedirs(src)
        for n, body in (("EL-A.colors", b"[Colors:View]\nA=1\n"), ("EL-B.colors", b"B=2\n")):
            with open(os.path.join(src, n), "wb") as fh:  # atomic-write: exempt — selftest fixture
                fh.write(body)
        d, snap = materialise(src, store)
        see("the snapshot is named by its content", os.path.basename(snap) == d)
        see("re-materialising unchanged input reuses the snapshot", materialise(src, store)[1] == snap)
        with open(os.path.join(src, "EL-A.colors"), "wb") as fh:  # atomic-write: exempt — fixture
            fh.write(b"[Colors:View]\nA=999\n")
        see("a rewritten source does not change the snapshot",
            open(os.path.join(snap, "EL-A.colors"), "rb").read() == b"[Colors:View]\nA=1\n"
            and verify(snap) == d)
        d2, snap2 = materialise(src, store)
        see("a changed source is a DIFFERENT snapshot", d2 != d and snap2 != snap)
        os.chmod(os.path.join(snap2, "EL-B.colors"), 0o644)
        with open(os.path.join(snap2, "EL-B.colors"), "wb") as fh:  # atomic-write: exempt — tamper fixture
            fh.write(b"B=tampered\n")
        try:
            verify(snap2)
            see("a tampered snapshot is REFUSED", False)
        except SnapshotError:
            see("a tampered snapshot is REFUSED", True)
        empty = os.path.join(td, "empty")
        os.makedirs(empty)
        try:
            materialise(empty, store)
            see("an empty source REFUSES", False)
        except SnapshotError:
            see("an empty source REFUSES", True)
        env = with_declared({ENV: "wheel.whl=/x"}, snap)
        see("the declared pair joins, not replaces, other artifacts",
            declared(env) == snap and "wheel.whl=/x" in env[ENV])
        see("a private build can UN-declare it", declared(with_declared(env, None)) is None
            and with_declared(env, None)[ENV] == "wheel.whl=/x")
        r = subprocess.run([sys.executable, os.path.abspath(__file__), "--where"],
                           env=with_declared(os.environ, snap), capture_output=True, text=True)
        see("a child handed the declared path reads IT", r.returncode == 0 and snap in r.stdout
            and "declared" in r.stdout)
        r = subprocess.run([sys.executable, os.path.abspath(__file__), "--where"],
                           env=with_declared(os.environ, os.path.join(store, "0" * 64)),
                           capture_output=True, text=True)
        see("a declared path that does not exist RAISES (no fallback ladder)", r.returncode != 0)
    print("schemes_artifact selftest:", "PASS" if ok else "FAIL")
    return ok


def _parsed_digest():
    """sha256 of make_preview.parse_scheme over every variant — what a READER got."""
    import make_preview
    got = {v: make_preview.parse_scheme(v) for v in variants()}
    return hashlib.sha256(json.dumps(got, sort_keys=True).encode()).hexdigest()


def race(readers=24, seconds=120.0):
    """The ORDERING, demonstrated in a scratch copy: while a writer process rewrites
    the copy's *.colors (atomically, alternating two palettes, as fast as it can),
    readers are started one after another.
      DECLARED arm: each reader is a process handed the snapshot taken BEFORE the
        writer started; it reports the digest it verified and what parse_scheme gave.
      CONTROL arm: the same number of reads of the copy's files BY PATH — the way
        parse_scheme read before W75 — digested.
    ⚑ THE CONTROL IS WHAT MAKES IT A MEASUREMENT: if the writer did not actually move
    the tree under the readers, the control shows one digest too, and "the snapshot
    readers agreed" would prove nothing."""
    import subprocess
    import time
    base = os.path.join(ROOT, ".build")
    os.makedirs(base, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="race-", dir=base) as td:
        src = os.path.join(td, "tree")
        os.makedirs(src)
        for n in members(ROOT):
            shutil.copy2(os.path.join(ROOT, n), os.path.join(src, n))
        d0, snap = materialise(src, os.path.join(td, "store"))
        # the alternate palette: every member with one extra line, so each rewrite
        # really changes the bytes (and so the digest) of the working copy
        writer_src = (
            "import os, sys, time\n"
            "src, until = sys.argv[1], time.time() + float(sys.argv[2])\n"
            "orig = {n: open(os.path.join(src, n), 'rb').read() for n in os.listdir(src)}\n"
            "i = 0\n"
            "stop = os.path.join(os.path.dirname(src), 'stop')\n"
            "while time.time() < until and not os.path.exists(stop):\n"
            "    i += 1\n"
            "    for n, b in orig.items():\n"
            "        t = os.path.join(src, '.w-' + n)\n"
            "        open(t, 'wb').write(b + (b'# rewrite %d\\n' % i if i % 2 else b''))\n"
            "        os.replace(t, os.path.join(src, n))\n"
            "print(i)\n")
        writer = subprocess.Popen([sys.executable, "-c", writer_src, src, str(seconds)],
                                  stdout=subprocess.PIPE, text=True)
        time.sleep(0.2)
        env = with_declared(os.environ, snap)
        declared_seen, parsed_seen, control_seen, failures = [], [], [], []
        for _ in range(readers):
            r = subprocess.run([sys.executable, os.path.abspath(__file__), "--json", "--parsed"],
                               env=env, capture_output=True, text=True)
            if r.returncode != 0:
                failures.append(r.stderr.strip().splitlines()[-1:])
                continue
            doc = json.loads(r.stdout)
            declared_seen.append(doc["digest"])
            parsed_seen.append(doc["parsed"])
            control_seen.append(digest(_read(src)))      # the pre-W75 read, by path
        with open(os.path.join(td, "stop"), "w"):  # atomic-write: exempt — an empty flag file
            pass
        writes = int((writer.communicate()[0] or "0").strip() or 0)
    return {"snapshot": d0, "readers": readers, "writer_rewrites": writes,
            "declared_distinct": sorted(set(declared_seen)),
            "declared_all_snapshot": bool(declared_seen) and set(declared_seen) == {d0},
            "parsed_distinct": len(set(parsed_seen)),
            "control_distinct": len(set(control_seen)),
            "reader_failures": failures, "n_declared": len(declared_seen)}


def main(argv):
    known = {"--materialise", "--where", "--json", "--selftest", "--race", "--parsed"}
    for a in argv[1:]:
        if a not in known:
            print(f"schemes_artifact: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    if "--race" in argv:
        m = race()
        print(json.dumps(m, indent=1))
        ok = (m["declared_all_snapshot"] and m["parsed_distinct"] == 1
              and m["n_declared"] == m["readers"] and m["control_distinct"] > 1)
        print(f"schemes_artifact race: {m['n_declared']} of {m['readers']} declared reader(s) saw "
              f"the snapshot digest {m['snapshot'][:16]}… ({m['parsed_distinct']} distinct "
              f"parse_scheme result(s)); the by-path control saw {m['control_distinct']} distinct "
              f"digest(s) over {m['writer_rewrites']} rewrite(s)"
              + ("" if m["control_distinct"] > 1 else
                 " — ⚑ the writer never moved the tree under the readers: NOT A MEASUREMENT"),
              file=sys.stdout if ok else sys.stderr)
        return 0 if ok else 1
    try:
        if "--materialise" in argv:
            d, p = materialise()
            print(f"{d} {p}")
            return 0
        r = resolve()
    except SnapshotError as e:
        print(f"schemes_artifact: REFUSED — {e}", file=sys.stderr)
        return 1
    ms = members(r["dir"])
    if "--json" in argv:
        doc = {"digest": r["digest"], "dir": r["dir"], "how": r["how"], "members": ms}
        if "--parsed" in argv:
            doc["parsed"] = _parsed_digest()
        print(json.dumps(doc, indent=1))
        return 0
    print(f"schemes_artifact: {len(ms)} member(s), digest {r['digest'][:16]}…\n"
          f"  dir: {r['dir']}\n  how: {r['how']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
