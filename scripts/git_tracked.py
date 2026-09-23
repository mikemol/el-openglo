#!/usr/bin/env python3
"""git_tracked.py — THE population authority for "which files are in this tree".

⚑ WHY (2026-09-22, 2026-09-23). Twice a check built its population by walking the
DISK from the repo root and descended into .claude/worktrees/ (agents' private
checkouts), .build/, .tree-writes/ or .ebuild-witness/. It counted files that are
not in this tree, and failed the gate on an agent's dangling symlink. The tree is
what git TRACKS, not what the directory holds; a skip-list of scratch dirs is only
the list we happen to know about today. So a population over the tree is
`git ls-files` with a pathspec, read here, once.

    scripts/git_tracked.py <pathspec>...   # the tracked paths, one per line; n on stderr
    scripts/git_tracked.py --source        # which authority answers here: git or walk
    scripts/git_tracked.py --selftest      # a scratch-dir file is NOT in the population

Pathspecs are git's: `*.py` matches at any depth, `:(glob)*.py` only at the top,
`templates` everything under it.

⚑ WHERE THERE IS NO GIT: THE Δ SANDBOX. paperkit's discriminator copies the tree
WITHOUT .git (layout._copy_sandbox ignores `.git` — the directory AND a worktree's
`.git` FILE) and runs the check there. check_mark learned that a git-only check
REFUSES in that copy and so can never be graded. So when `root` is not itself a git
work-tree top, the population is a WALK — bounded structurally, not by a name list:
  * a directory holding its own `.git` is another checkout, not this tree;
  * a directory holding its own `scripts/git_tracked.py` is a nested COPY of this
    tree (how the Δ sandbox presents .claude/worktrees/agent-*/ once their .git
    files are dropped);
  * a directory the root's `.gitignore` names (a trailing-`/` pattern) is declared
    not-the-tree by the same file git reads.
`source(root)` says which answered, so a caller can print it beside its n of m.

⚑ GIT_* PINS. Under a git hook, GIT_DIR / GIT_INDEX_FILE are exported and name THIS
repo, so `git -C ROOT ls-files` is still right there. Asked about ANOTHER root (a
fixture, a scratch copy), those pins would hand it OUR index — so for a foreign root
the child's environment is scrubbed of them (the same set check_tree_writes pops).

WEAKNESSES, stated: (1) a new file is in the population once it is `git add`ed —
exactly when a commit is about to certify it, but a hand run before staging will not
see it. (2) The walk fallback honours only `.gitignore`'s directory patterns and
`!`-less ones; it over-counts an ignored FILE pattern (e.g. `*.pyc`) — which a
caller's own pathspec almost always excludes anyway.
"""
import fnmatch
import os
import pathlib
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PINS = ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE", "GIT_PREFIX", "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES")
SELF = os.path.join("scripts", "git_tracked.py")


def scrubbed_env():
    """os.environ without git's repository pins — for git run against a FOREIGN repo."""
    return {k: v for k, v in os.environ.items() if k not in PINS}


def _env(root):
    return None if os.path.realpath(root) == os.path.realpath(ROOT) else scrubbed_env()


def source(root=ROOT):
    """'git' when `root` is a git work-tree TOP, else 'walk' (the Δ sandbox)."""
    r = subprocess.run(["git", "-C", root, "rev-parse", "--show-toplevel"],
                       capture_output=True, text=True, env=_env(root))
    top = r.stdout.strip()
    return "git" if r.returncode == 0 and top and os.path.realpath(top) == os.path.realpath(root) else "walk"


def _match(rel, spec):
    """git pathspec semantics, for the forms this tree uses."""
    if spec.startswith(":(glob)"):
        return pathlib.PurePosixPath(rel).full_match(spec[len(":(glob)"):])
    if any(c in spec for c in "*?["):
        return fnmatch.fnmatchcase(rel, spec)          # * crosses '/', as git's default
    s = spec.rstrip("/")
    return rel == s or rel.startswith(s + "/")


def _ignored_dirs(root):
    """Directory patterns from root's .gitignore (the `x/` lines, not negations)."""
    try:
        with open(os.path.join(root, ".gitignore"), encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return []
    return [ln.strip().rstrip("/") for ln in lines
            if ln.strip().endswith("/") and not ln.startswith(("#", "!"))]


def _walk(root, pathspecs):
    pats = _ignored_dirs(root)
    out = []
    # population: the NO-GIT fallback only (the Δ sandbox); pruned structurally — nested checkouts, nested copies of this tree, .gitignore'd dirs
    for dp, dns, fns in os.walk(root):
        keep = []
        for d in dns:
            full = os.path.join(dp, d)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if os.path.lexists(os.path.join(full, ".git")) or os.path.exists(os.path.join(full, SELF)):
                continue
            if any(fnmatch.fnmatchcase(rel, p.lstrip("/")) if p.startswith("/") or "/" in p
                   else fnmatch.fnmatchcase(d, p) for p in pats):
                continue
            keep.append(d)
        dns[:] = keep
        for f in fns:
            rel = os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/")
            if not pathspecs or any(_match(rel, s) for s in pathspecs):
                out.append(rel)
    return out


def files(*pathspecs, root=ROOT):
    """Sorted paths in the tree at `root`, relative with '/', matching the pathspecs
    (all when none is given). From `git ls-files` where root is a work tree, else the
    bounded walk above. Deleted-but-still-indexed paths are dropped: the population
    is what a reader can open."""
    if source(root) == "walk":
        out = _walk(root, pathspecs)
    else:
        r = subprocess.run(["git", "-C", root, "ls-files", "-z", "--", *pathspecs],
                           capture_output=True, check=True, env=_env(root))
        out = [p for p in r.stdout.decode("utf-8").split("\0") if p]
    return sorted(p for p in out if os.path.lexists(os.path.join(root, p)))


def paths(*pathspecs, root=ROOT):
    """files(), as absolute paths under `root`."""
    return [os.path.join(root, p) for p in files(*pathspecs, root=root)]


def init_fixture(d, add=None):
    """Make the tempdir `d` a git repo and track `add` (default: everything in it) —
    so a selftest's fixture goes through the SAME population path as the tree."""
    env = scrubbed_env()
    for args in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"]):
        subprocess.run(["git", "-C", d, *args], check=True, capture_output=True, env=env)
    subprocess.run(["git", "-C", d, "add", "--", *(add or ["."])], check=True,
                   capture_output=True, env=env)


def _plant(d, rels):
    for rel in rels:
        os.makedirs(os.path.dirname(os.path.join(d, rel)), exist_ok=True)
        with open(os.path.join(d, rel), "w") as fh:  # atomic-write: exempt — private fixture tempdir
            fh.write("x = 1\n")


def _selftest():
    import tempfile
    ok = True

    def see(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        ok = ok and cond

    scratch = [".claude/worktrees/x/c.py", ".build/d.py", "junk/e.py"]
    with tempfile.TemporaryDirectory() as d:
        _plant(d, ["a.py", "sub/b.py", "t.txt"] + scratch)
        init_fixture(d, ["a.py", "sub/b.py", "t.txt"])
        see("a git work tree is answered by git", source(d) == "git")
        got = files("*.py", root=d)
        see(f"tracked *.py are seen ({got})", got == ["a.py", "sub/b.py"])
        see("a scratch-dir file on disk is NOT in the population",
            not any(p.startswith((".claude/", ".build/", "junk/")) for p in got))
        see("`:(glob)*.py` does not recurse", files(":(glob)*.py", root=d) == ["a.py"])
        see("a directory pathspec takes what is under it", files("sub", root=d) == ["sub/b.py"])
    with tempfile.TemporaryDirectory() as d:
        # the Δ sandbox: no .git; a worktree copy whose .git file was dropped; an ignored dir
        _plant(d, ["a.py", "sub/b.py", "wt/scripts/git_tracked.py", "wt/a.py",
                   "co/a.py", "out/z.py", "deep/out/y.py"])
        _plant(d, ["co/.git"])
        with open(os.path.join(d, ".gitignore"), "w") as fh:  # atomic-write: exempt — private fixture tempdir
            fh.write("# c\nout/\n!keep/\n")
        see("a tree with no .git is answered by the walk", source(d) == "walk")
        got = files("*.py", root=d)
        see(f"the walk keeps the tree and drops copies, checkouts and ignored dirs ({got})",
            got == ["a.py", "sub/b.py"])
    live = files("*.py")
    see(f"the live tree has tracked .py files ({len(live)}, via {source()})", len(live) > 0)
    print("git_tracked selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    if argv[1:] == ["--selftest"]:
        return _selftest()
    if argv[1:] == ["--source"]:
        print(source())
        return 0
    for a in argv[1:]:
        if a.startswith("--"):
            print(f"git_tracked: unknown flag {a!r}", file=sys.stderr)
            return 2
    got = files(*argv[1:])
    for p in got:
        print(p)
    print(f"git_tracked: {len(got)} path(s) match {argv[1:] or ['(all)']} (via {source()})",
          file=sys.stderr)
    return 0 if got else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
