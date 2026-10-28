#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_tree_writes.py — which worklist claims' checks WRITE a tracked file?

⚑ WHY (W68).  The rule is: no gated check writes the real tree. @EMITTERS'
rule E3 fingerprints the tree around its own run, and in the first gate run
with it, it saw a tracked file change — written by ANOTHER check running in
parallel. E3 can say THAT the tree moved, not WHO moved it. This says who.

For EACH claim in catalog/worklist/warrants.bib (its `check` field, read with
substrate's bibstruct, resolved through paper.toml's `[checks.<type>] cmd`
templates the way worklist_gate._replay does; `concept:` the way
worklist_gate.cost does), SERIALLY:
  fingerprint (inode, mtime_ns, size) every tracked file of a scratch COPY
  (`git worktree add --detach`, the working tree's uncommitted diff applied to
  its index), run the check there, fingerprint again. A tracked file whose
  fingerprint moved was WRITTEN by that check. It is restored from the real
  tree before the next check, so one writer does not blame the next.
The copy is removed afterwards. The real tree is never a cwd.

    scripts/check_tree_writes.py                 # every claim; exit 0 iff none writes
    scripts/check_tree_writes.py --only A,B      # just those claims (n of m says so)
    scripts/check_tree_writes.py --json [--only A,B]   # the measurement, for policy/tree_writes.rego
    scripts/check_tree_writes.py --list          # each claim and the command it resolves to
    scripts/check_tree_writes.py --selftest      # the measurement can SEE a write

A claim whose check cannot run here — the command is not found (127), its
type is undeclared, or it exceeds the per-check timeout — is WITHHELD, not
admitted: it was not observed not to write.

WEAKNESS, STATED.  The checks run ONE AT A TIME, so this sees writes and
cannot see races: it never reproduces the interleaving that made @EMITTERS
flake. Its value is the converse — a race over a tracked file needs a writer,
so 0 writers here over every claim means no such race is POSSIBLE. It also
sees tracked files only (untracked build products are not the gate's inputs
by definition), and a check that writes only under some input it did not get
this run is not seen. It is heavy: it runs every claim's check (use --only).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ⚑ A GIT HOOK PINS THE REPOSITORY THROUGH THE ENVIRONMENT, AND IT MUST NOT LEAK.
# Under pre-commit, git exports GIT_DIR / GIT_INDEX_FILE (and friends) naming
# MAIN's repo and index. Every git call here names its repo with -C, but those
# variables override -C's discovery — measured 2026-09-23: this selftest passed
# run by hand and died in the hook with `git worktree add` exit 128, because the
# fixture repo's git was handed main's index. And a check run in the scratch copy
# would inherit them too, reading MAIN's index while certifying the copy. So the
# pins are scrubbed once, for this process and every child.
import git_tracked

for _pin in git_tracked.PINS:
    os.environ.pop(_pin, None)
WORKLIST = os.path.join("catalog", "worklist")
CACHE = ".palette-cache.json"
TIMEOUT = 900


def claims(root=ROOT):
    """[(key, check)] from warrants.bib, read by paperkit's parser (worklist_gate.warrants).

    Refuses — raises — when the engine is absent: an empty claim list would read
    as "no check writes" over nothing."""
    import worklist_gate

    recs = worklist_gate.warrants(os.path.join(root, WORKLIST, "warrants.bib"))
    if recs is None:
        raise RuntimeError("paperkit not found: cannot read the claims")
    return [(k, r["check"].strip()) for k, r in recs.items() if r.get("check")]


def resolve(check, root=ROOT):
    """(shell command run with cwd=catalog/worklist, None) or (None, why)."""
    kind, _, target = check.partition(":")
    target = target.strip()
    if kind == "concept":
        return f"python3 ../library/concepts.py {target}", None
    with open(os.path.join(root, WORKLIST, "paper.toml"), "rb") as fh:
        decl = tomllib.load(fh).get("checks", {})
    tmpl = decl.get(kind, {}).get("cmd")
    if not tmpl:
        return None, f"paper.toml declares no `{kind}` check type"
    return tmpl.replace("{target}", target), None


def tracked(root):
    """Every tracked path of the scratch copy — scripts/git_tracked.py (W61 N4; this
    was a second `git ls-files -z` copy). `root` is never this repo here, so
    git_tracked runs git with the GIT_* pins scrubbed, whatever this process holds."""
    import git_tracked

    return git_tracked.files(root=root)


def fingerprint(root, paths):
    out = {}
    for p in paths:
        try:
            st = os.lstat(os.path.join(root, p))
            out[p] = (st.st_ino, st.st_mtime_ns, st.st_size)
        except OSError:
            out[p] = None
    return out


def make_copy(src, parent):
    """A detached worktree of `src` with its uncommitted diff applied to the index."""
    copy = os.path.join(parent, "tree")
    subprocess.run(
        ["git", "-C", src, "worktree", "add", "-q", "--detach", copy, "HEAD"],
        check=True,
        capture_output=True,
    )
    diff = subprocess.run(
        ["git", "-C", src, "diff", "--binary", "HEAD"], capture_output=True, check=True
    ).stdout
    if diff:
        subprocess.run(
            ["git", "-C", copy, "apply", "--index", "--whitespace=nowarn"],
            input=diff,
            check=True,
            capture_output=True,
        )
    # new, not-yet-added files are part of the tree being certified too. This runs only in
    # a real repo (it just built a `git worktree`), and asks what git_tracked does not answer.
    # population: UNTRACKED files (--others) of a real repo — not the tree git_tracked reads
    untracked = subprocess.run(
        [
            "git",
            "-C",
            src,
            "ls-files",
            "-z",
            "--others",
            "--exclude-standard",
            "--exclude=.tree-writes/",
        ],
        capture_output=True,
        check=True,
    )
    new = untracked.stdout.decode("utf-8").split("\0")
    new = [p for p in new if p and not os.path.isdir(os.path.join(src, p))]
    for p in new:
        os.makedirs(os.path.dirname(os.path.join(copy, p)), exist_ok=True)
        shutil.copy2(
            os.path.join(src, p), os.path.join(copy, p), follow_symlinks=False
        )  # atomic-write: exempt — into the private copy
    if new:
        subprocess.run(
            ["git", "-C", copy, "add", "--"] + new, check=True, capture_output=True
        )
    if os.path.isfile(os.path.join(src, CACHE)):
        shutil.copy2(
            os.path.join(src, CACHE), os.path.join(copy, CACHE)
        )  # atomic-write: exempt — into the private copy
    return copy


def drop_copy(src, copy):
    subprocess.run(
        ["git", "-C", src, "worktree", "remove", "--force", copy],
        capture_output=True,
        check=False,
    )
    shutil.rmtree(copy, ignore_errors=True)
    subprocess.run(
        ["git", "-C", src, "worktree", "prune"], capture_output=True, check=False
    )


def restore(src, copy, paths):
    for p in paths:
        s, d = os.path.join(src, p), os.path.join(copy, p)
        if os.path.lexists(d) and not os.path.islink(d) and os.path.isdir(d):
            shutil.rmtree(d)
        elif os.path.lexists(d):
            os.unlink(d)
        if os.path.lexists(s):
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(
                s, d, follow_symlinks=False
            )  # atomic-write: exempt — restoring the private copy


def measure(root=ROOT, only=None, timeout=TIMEOUT, population=None):
    """The --json document. `population` overrides the claims (selftest)."""
    every = population if population is not None else claims(root)
    chosen = [c for c in every if only is None or c[0] in only]
    env = dict(
        os.environ,
        PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get("PATH", ""),
        OPENBLAS_NUM_THREADS="1",
    )
    cases, withheld = [], []
    # ⚑ UNDER THE REPO, NOT /tmp: @EBUILD stages under sys-apps/sandbox with
    # SANDBOX_DENY=/tmp, and its work dir is inside whatever tree it runs in.
    # ⚑ NOT /var/tmp EITHER, MEASURED (2026-09-25, luthen asked to move this off md0):
    # --only EBUILD exits 1 from a /var/tmp copy and 0 from the in-repo one, all else
    # equal. Where it CAN live off md0 is open (R11). EL_TREE_WRITES_DIR overrides.
    work = os.environ.get("EL_TREE_WRITES_DIR", os.path.join(root, ".tree-writes"))
    os.makedirs(work, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="el-", dir=work) as parent:
        copy = make_copy(root, parent)
        try:
            paths = tracked(copy)
            cwd = os.path.join(copy, WORKLIST)
            for key, check in chosen:
                cmd, why = resolve(check, copy)
                if cmd is None:
                    withheld.append({"key": key, "check": check, "withheld": why})
                    continue
                before = fingerprint(copy, paths)
                try:
                    r = subprocess.run(
                        cmd,
                        shell=True,
                        cwd=cwd,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        check=False,
                    )
                    rc = r.returncode
                except subprocess.TimeoutExpired:
                    rc = None
                after = fingerprint(copy, paths)
                written = sorted(p for p in paths if before[p] != after[p])
                if written:
                    restore(root, copy, written)
                if rc is None or rc == 127:
                    withheld.append(
                        {
                            "key": key,
                            "check": check,
                            "written": written,
                            "withheld": (
                                f"exceeded {timeout} s"
                                if rc is None
                                else "command not found (127)"
                            ),
                        }
                    )
                    continue
                cases.append({"key": key, "check": check, "rc": rc, "written": written})
        finally:
            drop_copy(root, copy)
    return {
        "cases": cases,
        "withheld": withheld,
        "claims": len(every),
        "measured": len(chosen),
        "tracked": len(paths),
        "not_measured": sorted(
            k for k, _ in every if only is not None and k not in only
        ),
    }


def untracked(root):
    """Every untracked path of `root`, gitignored ones included (the emitted dirs are ignored)."""
    # population: UNTRACKED files (--others, ignored included) of the scratch copy of a real repo
    out = subprocess.run(
        ["git", "-C", root, "ls-files", "-z", "--others"],
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8")
    return sorted(p for p in out.split("\0") if p)


def readers(paths, sources):
    """({path: [source, ...]}, [path]) — which make_deb mapping sources read each written path: a
    source reads a path when it is that path or a directory above it. The second value is the paths
    NO source reads (caches and bytecode a staging writes and never ships), listed, never dropped."""
    attributed, orphans = {}, []
    for p in paths:
        hit = sorted(s for s in sources if p == s or p.startswith(s.rstrip("/") + "/"))
        if hit:
            attributed[p] = hit
        else:
            orphans.append(p)
    return attributed, orphans


def generator_writes(root=ROOT, modules=None, timeout=TIMEOUT):
    """{module: {rc, tracked, new}} for each emitters.STAGE generator run ALONE as __main__ in a
    scratch copy, from the copy's root (W775): which TRACKED files its run changes, and which
    untracked or ignored files it creates. The generators run in STAGE order and are not restored
    between, so a later one reads the earlier ones' outputs, as make_deb.stage runs them.
    WEAKNESS: a generator that rewrites a file with the same bytes shows as tracked only if its
    mtime or inode moved, which atomic_write always does; one that creates nothing new and
    changes nothing is listed with empty lists, never dropped."""
    if modules is None:
        if root not in sys.path:
            sys.path.insert(0, root)
        import emitters

        chosen = list(emitters.STAGE)
    else:
        chosen = list(modules)
    env = dict(
        os.environ,
        PATH=os.path.dirname(sys.executable) + os.pathsep + os.environ.get("PATH", ""),
        OPENBLAS_NUM_THREADS="1",
    )
    work = os.environ.get("EL_TREE_WRITES_DIR", os.path.join(root, ".tree-writes"))
    os.makedirs(work, exist_ok=True)
    out = {}
    with tempfile.TemporaryDirectory(prefix="el-", dir=work) as parent:
        copy = make_copy(root, parent)
        try:
            paths = tracked(copy)
            for mod in chosen:
                before = fingerprint(copy, paths)
                had = set(untracked(copy))
                try:
                    r = subprocess.run(
                        [sys.executable, mod + ".py"],
                        cwd=copy,
                        env=env,
                        capture_output=True,
                        text=True,
                        timeout=timeout,
                        check=False,
                    )
                    rc = r.returncode
                except subprocess.TimeoutExpired:
                    rc = None
                after = fingerprint(copy, paths)
                out[mod] = {
                    "rc": rc,
                    "tracked": sorted(p for p in paths if before[p] != after[p]),
                    "new": sorted(set(untracked(copy)) - had),
                }
        finally:
            drop_copy(root, copy)
    return out


def main(argv):
    args, only, i = argv[1:], None, 0
    flags = set()
    while i < len(args):
        a = args[i]
        if a == "--only":
            if i + 1 >= len(args):
                print("check_tree_writes: --only needs KEY[,KEY…]", file=sys.stderr)
                return 2
            only = set(args[i + 1].split(","))
            i += 2
            continue
        if a not in ("--json", "--list", "--generators"):
            print(f"check_tree_writes: unknown flag {a!r}", file=sys.stderr)
            return 2
        flags.add(a)
        i += 1
    if "--generators" in flags:
        doc = generator_writes()
        if "--json" in flags:
            print(json.dumps(doc, indent=1))
            return 0
        import make_deb

        sources = [
            s for s, _d in make_deb.system_mapping() + make_deb.helper_source_mapping()
        ]
        n_paths = n_read = 0
        for mod, rec in doc.items():
            both = rec["tracked"] + rec["new"]
            attributed, orphans = readers(both, sources)
            n_paths += len(both)
            n_read += len(attributed)
            tops = sorted({p.split("/", 1)[0] for p in rec["new"]})
            print(
                f"  {mod:16s} rc {rec['rc']}  tracked changed {len(rec['tracked'])}  "
                f"new {len(rec['new'])}  read by a mapping source {len(attributed)}, "
                f"by none {len(orphans)}  (new under {', '.join(tops) or '-'})"
            )
            for p in rec["tracked"]:
                print(
                    f"      tracked {p}  <- {', '.join(attributed.get(p, ['NO SOURCE']))}"
                )
        written = sum(1 for r in doc.values() if r["tracked"] or r["new"])
        print(
            f"check_tree_writes: {written} of {len(doc)} STAGE generator(s) write the real "
            f"tree; {n_read} of {n_paths} written path(s) are read by a make_deb mapping "
            f"source (the rest are written and not shipped: bytecode, build caches, SVG and "
            f"preview intermediates)"
        )
        return 0
    if "--list" in flags:
        for key, check in claims():
            cmd, why = resolve(check)
            print(f"{key:20s} {cmd or 'WITHHELD: ' + why}")
        return 0
    if only is not None:
        unknown = only - {k for k, _ in claims()}
        if unknown:
            print(
                f"check_tree_writes: no such claim(s): {sorted(unknown)}",
                file=sys.stderr,
            )
            return 2
    doc = measure(only=only)
    if "--json" in flags:
        print(json.dumps(doc, indent=1))
        return 0
    writers = [c for c in doc["cases"] + doc["withheld"] if c.get("written")]
    for c in writers:
        print(
            f"    WRITES {c['key']} ({c['check']}): {', '.join(c['written'])}",
            file=sys.stderr,
        )
    for w in doc["withheld"]:
        print(f"    WITHHELD {w['key']}: {w['withheld']}", file=sys.stderr)
    bad = bool(writers) or not doc["cases"]
    print(
        f"check_tree_writes: {len(writers)} of {doc['measured']} measured claim(s) write "
        f"the tree ({len(doc['withheld'])} withheld; {doc['measured']} of {doc['claims']} "
        f"claims measured; {doc['tracked']} tracked files fingerprinted)"
        + (
            f"; not measured: {', '.join(doc['not_measured'])}"
            if doc["not_measured"]
            else ""
        ),
        file=sys.stderr if bad else sys.stdout,
    )
    return 1 if bad else 0


def _selftest():
    """The measurement SEES a write to a tracked file, a same-bytes rewrite, and
    names the right claim; a clean check and a missing command are not blamed."""
    ok = True

    def see(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        ok = ok and cond

    got = claims()
    see(f"the real population is non-empty ({len(got)} claims)", len(got) > 0)
    see(
        "tool: resolves through paper.toml",
        (resolve("tool:x.py --y")[0] or "").endswith("python3 ../../scripts/x.py --y"),
    )
    see("an undeclared type is refused", resolve("nosuch:z")[0] is None)
    with tempfile.TemporaryDirectory() as repo:
        os.makedirs(os.path.join(repo, WORKLIST))
        files = {
            "out.txt": "A\n",
            "same.txt": "S\n",
            os.path.join(WORKLIST, "paper.toml"): '[checks.cmd]\ncmd = "{target}"\n',
        }
        for name, body in files.items():
            with open(
                os.path.join(repo, name), "w"
            ) as fh:  # atomic-write: exempt — selftest fixture
                fh.write(body)
        for c in (
            ["init", "-q"],
            ["add", "."],
            ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"],
        ):
            subprocess.run(["git", "-C", repo] + c, check=True)
        pop = [
            ("WRITER", "cmd:echo B > ../../out.txt"),
            ("CLEAN", "cmd:true"),
            (
                "SAMEBYTES",
                "cmd:cp ../../same.txt ../../s2 && mv ../../s2 ../../same.txt",
            ),
            ("NOCMD", "cmd:no-such-command-el-openglo"),
        ]
        doc = measure(repo, population=pop)
        by = {c["key"]: c for c in doc["cases"]}
        see(
            "a check that writes a tracked file is SEEN",
            by.get("WRITER", {}).get("written") == ["out.txt"],
        )
        see(
            "a same-bytes rewrite is SEEN",
            by.get("SAMEBYTES", {}).get("written") == ["same.txt"],
        )
        see(
            "a clean check is not blamed (the writer was restored)",
            by.get("CLEAN", {}).get("written") == [],
        )
        see(
            "a missing command is WITHHELD, not admitted",
            [w["key"] for w in doc["withheld"]] == ["NOCMD"],
        )
        see("the population is counted", doc["claims"] == 4 and doc["measured"] == 4)
        with open(os.path.join(repo, "out.txt")) as fh:
            out_txt = fh.read()
        see("the real fixture tree was not written", out_txt == "A\n")
        wl = subprocess.run(
            ["git", "-C", repo, "worktree", "list"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        see("the scratch worktree was removed", len(wl.splitlines()) == 1)
    # W775: a generator run alone is attributed its tracked rewrite and its new file, and nothing else
    with tempfile.TemporaryDirectory() as repo:
        stub = (
            'open("out.txt", "w").write("B\\n")\nopen("new.txt", "w").write("N\\n")\n'
        )
        for name, body in (("make_stub.py", stub), ("out.txt", "A\n")):
            with open(
                os.path.join(repo, name), "w"
            ) as fh:  # atomic-write: exempt — selftest fixture
                fh.write(body)
        for c in (
            ["init", "-q"],
            ["add", "."],
            ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"],
        ):
            subprocess.run(["git", "-C", repo] + c, check=True)
        gen = generator_writes(repo, ["make_stub"])["make_stub"]
        see(
            "a generator run alone: its tracked rewrite and its new file, attributed (W775)",
            (gen["rc"], gen["tracked"], gen["new"]) == (0, ["out.txt"], ["new.txt"]),
        )
    got, orphans = readers(["a/b.txt", "c.txt", "d/e"], ["a", "c.txt"])
    see(
        "readers: a directory source reads what is under it, a file its own path, an unread path is listed",
        (got, orphans) == ({"a/b.txt": ["a"], "c.txt": ["c.txt"]}, ["d/e"]),
    )
    print("check_tree_writes selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
