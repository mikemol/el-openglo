#!/usr/bin/env bash
# THE GATE OVER THE STAGED TREE, NOT THE WORKING TREE (W498, under W459). `.githooks/pre-commit` runs this;
# it runs `bazel test //:precommit` over a copy of the INDEX, so the verdict is about the bytes being
# committed. The two diverge exactly when `git add` is partial, which is the normal case: a gate that reads
# the working tree blesses bytes that are not the ones landing (mtools' pre-commit, its first rule).
#
#   gate/staged.sh [BAZEL_ARGS...]        run //:precommit over the staged tree (extra args go to bazel test)
#   gate/staged.sh --materialise          only (re)build the staged tree and print its path
#
# ⚑ A STABLE PATH, NOT mktemp: bazel's output base is a hash of the workspace path, so a fresh directory per
# run is a cold ACTION cache even when the disk cache holds every result (mtools measured 187 analysis
# actions redone with 0 test reruns). The directory is wiped and refreshed from the index each run and NOT
# removed on exit, so it never holds stale content and keeps its output base.
#
# ⚑ THE INDEX IS NAMED ABSOLUTELY. git exports GIT_INDEX_FILE (relative, `.git/next-index-N.lock`, under a
# partial commit) into the hook; the staged tree is not inside a repository, so every git call there needs
# the repository and THAT index named by absolute path (GIT_DIR, GIT_INDEX_FILE). The same two names reach
# the stages (`--test_env`, .bazelrc) so check_ebuild certifies the commit's own index.
#
# ⚑ THE HOST'S UNTRACKED STATE IS LINKED, NOT COPIED: the venv, the warm palette cache and the gitignored
# emitted outputs the stages read (aurorae/, plasma/, screens' sibling outputs ...) live only in the real
# checkout. A symlink gives the staged tree the same view of them while the TRACKED files stay the index's,
# so @CURRENCY compares the staged inputs against the host's outputs, which is the question.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
# ⚑ NOT UNDER /tmp OR /var/tmp: check_ebuild stages inside the tree under portage's sandbox with
# SANDBOX_DENY=/tmp:/var/tmp, and DENY covers READS, so a staged tree there cannot read its own venv
# ("open_rd deny /var/tmp/el-openglo-staged/.venv/pyvenv.cfg", measured 2026-10-11). The home cache is the
# peers' choice too (mtools-staged).
STAGED="${EL_STAGED_DIR:-/home/mikemol/.cache/el-openglo-staged}"
GITDIR="$(git rev-parse --absolute-git-dir)"
INDEX="${GIT_INDEX_FILE:-$GITDIR/index}"
case "$INDEX" in
  /*) ;;
  *) INDEX="$ROOT/$INDEX" ;;
esac

# git against the STAGED repository, with none of the commit's GIT_* (they name the REAL repository)
sgit() {
  env -u GIT_DIR -u GIT_INDEX_FILE -u GIT_WORK_TREE -u GIT_PREFIX git -C "$STAGED" "$@"
}

materialise() {
  rm -rf "$STAGED"
  mkdir -p "$STAGED"
  GIT_DIR="$GITDIR" GIT_INDEX_FILE="$INDEX" git -C "$ROOT" checkout-index --all --prefix="$STAGED/"
  # ⚑ THE STAGED TREE IS ITS OWN REPOSITORY, whose index is exactly the commit's tree. Everything that asks
  # "what is tracked" (bazel's tracked_files rule, git_tracked, check_ebuild's write-tree) then answers
  # natively and needs NO GIT_* from the commit. Without a repository git_tracked fell back to a directory
  # walk that listed the host-state symlinks below, and check_ebuild / check_emitters_run copied them as
  # symlinks ("SameFileError", measured 2026-10-11 on the first full run).
  sgit init -q
  # the host's untracked, gitignored state: one symlink per top-level ignored entry (a directory is one
  # entry), skipping what must stay per-tree (bazel's links, bytecode, worktrees, scratch dirs, .git).
  # ⚑ EACH LINK IS EXCLUDED FROM THE STAGED INDEX BY NAME: a .gitignore pattern `dir/` matches a directory,
  # not a symlink named `dir`, so `git add -A` would otherwise track the link (15 extra entries, measured).
  while IFS= read -r -d '' entry; do
    entry="${entry%/}"
    case "$entry" in
      bazel-* | __pycache__ | */__pycache__ | .git | .claude/worktrees | .ebuild-witness | .tree-writes | .gate-outcomes.tsv) continue ;;
    esac
    [ -e "$STAGED/$entry" ] || [ -L "$STAGED/$entry" ] && continue
    mkdir -p "$STAGED/$(dirname "$entry")"
    ln -s "$ROOT/$entry" "$STAGED/$entry"
  done < <(git -C "$ROOT" ls-files -z --others --ignored --exclude-standard --directory)
  # the ledger is the real tree's: gate timings accumulate across commits, not in a throwaway copy
  touch "$ROOT/.gate-outcomes.tsv"
  ln -s "$ROOT/.gate-outcomes.tsv" "$STAGED/.gate-outcomes.tsv"
  # ⚑ THE STAGED INDEX IS THE COMMIT'S LIST, ADDED BY NAME AND FORCED (-f), NOT `git add -A`: add -A obeys
  # ignore rules, so a tracked file an ignore pattern matches (.claude/settings.local.json) was left out,
  # and the host-state links above would be added unless every one were excluded. The list is the
  # authority; the links are simply not on it.
  sgit add -f --pathspec-from-file=<(GIT_DIR="$GITDIR" GIT_INDEX_FILE="$INDEX" git -C "$ROOT" ls-files -z) --pathspec-file-nul
}

materialise
if [ "${1:-}" = "--materialise" ]; then
  printf '%s\n' "$STAGED"
  exit 0
fi

cd "$STAGED"
# no GIT_* for the stages: they read the staged repository above, never the commit's
unset GIT_DIR GIT_INDEX_FILE GIT_WORK_TREE GIT_PREFIX
exec bazel test "${EL_STAGED_TARGET:-//:precommit}" --noshow_progress "$@"
