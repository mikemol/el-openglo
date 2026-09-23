#!/usr/bin/env python3
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
for _pin in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE", "GIT_PREFIX", "GIT_COMMON_DIR",
             "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES"):
    os.environ.pop(_pin, None)
WORKLIST = os.path.join("catalog", "worklist")
BIBSTRUCT = os.path.expanduser("~/github/substrate/scratch/bibstruct.py")
CACHE = ".palette-cache.json"
TIMEOUT = 900


def claims(root=ROOT):
    """[(key, check)] from warrants.bib, read by bibstruct --field check."""
    r = subprocess.run([sys.executable, BIBSTRUCT, "--field", "check",
                        os.path.join(root, WORKLIST, "warrants.bib")],
                       capture_output=True, text=True, check=True)
    out = []
    for line in r.stdout.splitlines():
        if not line.startswith("  "):
            continue                       # the "check: n of m entries" summary
        key, _, check = line.strip().partition(" ")
        out.append((key, check.strip()))
    return out


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
    r = subprocess.run(["git", "-C", root, "ls-files", "-z"], capture_output=True, check=True)
    return [p for p in r.stdout.decode("utf-8").split("\0") if p]


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
    subprocess.run(["git", "-C", src, "worktree", "add", "-q", "--detach", copy, "HEAD"],
                   check=True, capture_output=True)
    diff = subprocess.run(["git", "-C", src, "diff", "--binary", "HEAD"],
                          capture_output=True, check=True).stdout
    if diff:
        subprocess.run(["git", "-C", copy, "apply", "--index", "--whitespace=nowarn"],
                       input=diff, check=True, capture_output=True)
    # new, not-yet-added files are part of the tree being certified too
    new = subprocess.run(["git", "-C", src, "ls-files", "-z", "--others", "--exclude-standard",
                          "--exclude=.tree-writes/"],
                         capture_output=True, check=True).stdout.decode("utf-8").split("\0")
    new = [p for p in new if p and not os.path.isdir(os.path.join(src, p))]
    for p in new:
        os.makedirs(os.path.dirname(os.path.join(copy, p)), exist_ok=True)
        shutil.copy2(os.path.join(src, p), os.path.join(copy, p), follow_symlinks=False)  # atomic-write: exempt — into the private copy
    if new:
        subprocess.run(["git", "-C", copy, "add", "--"] + new, check=True, capture_output=True)
    if os.path.isfile(os.path.join(src, CACHE)):
        shutil.copy2(os.path.join(src, CACHE), os.path.join(copy, CACHE))  # atomic-write: exempt — into the private copy
    return copy


def drop_copy(src, copy):
    subprocess.run(["git", "-C", src, "worktree", "remove", "--force", copy],
                   capture_output=True)
    shutil.rmtree(copy, ignore_errors=True)
    subprocess.run(["git", "-C", src, "worktree", "prune"], capture_output=True)


def restore(src, copy, paths):
    for p in paths:
        s, d = os.path.join(src, p), os.path.join(copy, p)
        if os.path.lexists(d) and not os.path.islink(d) and os.path.isdir(d):
            shutil.rmtree(d)
        elif os.path.lexists(d):
            os.unlink(d)
        if os.path.lexists(s):
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d, follow_symlinks=False)  # atomic-write: exempt — restoring the private copy


def measure(root=ROOT, only=None, timeout=TIMEOUT, population=None):
    """The --json document. `population` overrides the claims (selftest)."""
    every = population if population is not None else claims(root)
    chosen = [c for c in every if only is None or c[0] in only]
    env = dict(os.environ, PATH=os.path.dirname(sys.executable) + os.pathsep
               + os.environ.get("PATH", ""), OPENBLAS_NUM_THREADS="1")
    cases, withheld = [], []
    # ⚑ UNDER THE REPO, NOT /tmp: @EBUILD stages under sys-apps/sandbox with
    # SANDBOX_DENY=/tmp, and its work dir is inside whatever tree it runs in.
    work = os.path.join(root, ".tree-writes")
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
                    r = subprocess.run(cmd, shell=True, cwd=cwd, env=env, capture_output=True,
                                       text=True, timeout=timeout)
                    rc = r.returncode
                except subprocess.TimeoutExpired:
                    rc = None
                after = fingerprint(copy, paths)
                written = sorted(p for p in paths if before[p] != after[p])
                if written:
                    restore(root, copy, written)
                if rc is None or rc == 127:
                    withheld.append({"key": key, "check": check, "written": written,
                                     "withheld": (f"exceeded {timeout} s" if rc is None
                                                  else "command not found (127)")})
                    continue
                cases.append({"key": key, "check": check, "rc": rc, "written": written})
        finally:
            drop_copy(root, copy)
    return {"cases": cases, "withheld": withheld, "claims": len(every),
            "measured": len(chosen), "tracked": len(paths),
            "not_measured": sorted(k for k, _ in every if only is not None and k not in only)}


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
        if a not in ("--json", "--list"):
            print(f"check_tree_writes: unknown flag {a!r}", file=sys.stderr)
            return 2
        flags.add(a)
        i += 1
    if "--list" in flags:
        for key, check in claims():
            cmd, why = resolve(check)
            print(f"{key:20s} {cmd or 'WITHHELD: ' + why}")
        return 0
    if only is not None:
        unknown = only - {k for k, _ in claims()}
        if unknown:
            print(f"check_tree_writes: no such claim(s): {sorted(unknown)}", file=sys.stderr)
            return 2
    doc = measure(only=only)
    if "--json" in flags:
        print(json.dumps(doc, indent=1))
        return 0
    writers = [c for c in doc["cases"] + doc["withheld"] if c.get("written")]
    for c in writers:
        print(f"    WRITES {c['key']} ({c['check']}): {', '.join(c['written'])}", file=sys.stderr)
    for w in doc["withheld"]:
        print(f"    WITHHELD {w['key']}: {w['withheld']}", file=sys.stderr)
    bad = bool(writers) or not doc["cases"]
    print(f"check_tree_writes: {len(writers)} of {doc['measured']} measured claim(s) write "
          f"the tree ({len(doc['withheld'])} withheld; {doc['measured']} of {doc['claims']} "
          f"claims measured; {doc['tracked']} tracked files fingerprinted)"
          + (f"; not measured: {', '.join(doc['not_measured'])}" if doc["not_measured"] else ""),
          file=sys.stderr if bad else sys.stdout)
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
    see("tool: resolves through paper.toml", resolve("tool:x.py --y")[0] == "python3 ../../scripts/x.py --y")
    see("an undeclared type is refused", resolve("nosuch:z")[0] is None)
    with tempfile.TemporaryDirectory() as repo:
        os.makedirs(os.path.join(repo, WORKLIST))
        files = {"out.txt": "A\n", "same.txt": "S\n",
                 os.path.join(WORKLIST, "paper.toml"): '[checks.cmd]\ncmd = "{target}"\n'}
        for name, body in files.items():
            with open(os.path.join(repo, name), "w") as fh:  # atomic-write: exempt — selftest fixture
                fh.write(body)
        for c in (["init", "-q"], ["add", "."],
                  ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"]):
            subprocess.run(["git", "-C", repo] + c, check=True)
        pop = [("WRITER", "cmd:echo B > ../../out.txt"),
               ("CLEAN", "cmd:true"),
               ("SAMEBYTES", "cmd:cp ../../same.txt ../../s2 && mv ../../s2 ../../same.txt"),
               ("NOCMD", "cmd:no-such-command-el-openglo")]
        doc = measure(repo, population=pop)
        by = {c["key"]: c for c in doc["cases"]}
        see("a check that writes a tracked file is SEEN", by.get("WRITER", {}).get("written") == ["out.txt"])
        see("a same-bytes rewrite is SEEN", by.get("SAMEBYTES", {}).get("written") == ["same.txt"])
        see("a clean check is not blamed (the writer was restored)", by.get("CLEAN", {}).get("written") == [])
        see("a missing command is WITHHELD, not admitted",
            [w["key"] for w in doc["withheld"]] == ["NOCMD"])
        see("the population is counted", doc["claims"] == 4 and doc["measured"] == 4)
        see("the real fixture tree was not written",
            open(os.path.join(repo, "out.txt")).read() == "A\n")
        wl = subprocess.run(["git", "-C", repo, "worktree", "list"], capture_output=True, text=True).stdout
        see("the scratch worktree was removed", len(wl.splitlines()) == 1)
    print("check_tree_writes selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
