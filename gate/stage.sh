#!/usr/bin/env bash
# ONE GATE STAGE, run as one bazel test target (W490, under W489/W457). gate/precommit.sh is the whole
# gate as one script; this is the same stages one at a time, so each is its own target with its own
# log and verdict (BuildBuddy keeps each, a flake names the stage that flaked).
#
#   gate/stage.sh selftest scripts/check_x.py   a check's --selftest (and worklist_gate's)
#   gate/stage.sh opa-test                      every policy's refusing and admitting case
#   gate/stage.sh segment-lattice               segment_topology's own invariants
#   gate/stage.sh worklist                      every cited claim of catalog/worklist is discharged
#   gate/stage.sh readme                        README.md is the projection and its claims hold
#
# Exit: the stage's own. A stage that cannot run is refused (2), never a pass.
#
# ⚑ THE PALETTE CACHE IS WARMED HERE, BY EVERY STAGE THAT SOLVES THE PALETTE. precommit.sh warms it
# once, in order, before the worklist. Bazel orders no tests, so a stage that imports make_schemes would
# meet a COLD cache (~108 s) and, under paperkit's per-check budget, time out and refuse a green tree
# (three times on 2026-09-20). The warm step is cheap when warm and flock-serialised when cold, so
# putting it in each stage is correct and order-free. opa-test and segment-lattice never solve it.
#
# ⚑ THE ENVIRONMENT DISCIPLINE IS precommit.sh's, unchanged (see its comments for the measurements):
# a selftest runs without the commit's GIT_* (it builds throwaway repos; the inherited index made
# seven read empty populations), EXCEPT check_ebuild, which certifies the staged tree and needs them;
# the gates keep the environment, and the commit's index reaches paperkit's default-deny check
# sandbox under a PAPERKIT_ name.
set -uo pipefail

usage() {
  echo "gate/stage.sh: REFUSED — usage: stage.sh selftest SCRIPT | opa-test | segment-lattice | worklist | readme" >&2
  exit 2
}

[ $# -ge 1 ] || usage
KIND="$1"
SCRIPT="${2:-}"

# THE REPO ROOT IS RESOLVED FROM A DECLARED FILE, NOT FROM THE CWD (a test's cwd is its runfiles dir)
if [ -n "${TEST_SRCDIR:-}" ] && [ -e "${TEST_SRCDIR}/${TEST_WORKSPACE:-_main}/MODULE.bazel" ]; then
  ROOT="$(dirname "$(readlink -f "${TEST_SRCDIR}/${TEST_WORKSPACE:-_main}/MODULE.bazel")")"
else
  ROOT="$(git rev-parse --show-toplevel)"
fi
cd "$ROOT" || exit 1

LEDGER="$ROOT/.gate-outcomes.tsv"

if [ -d "$ROOT/.venv" ] && command -v uv >/dev/null 2>&1; then
  RUNNER=(uv run --no-sync python3)
else
  RUNNER=(python3)
fi

export PAPERKIT_GIT_INDEX_FILE="${GIT_INDEX_FILE:-}"

# the gate's capture point: time the stage and append its outcome to the ledger
run() {
  local name="$1"; shift
  local start end rc
  start=$(date +%s%N)
  "$@"
  rc=$?
  end=$(date +%s%N)
  printf '%s\t%s\t%d\t%d\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$name" "$rc" \
      "$(( (end - start) / 1000000 ))" >> "$LEDGER"
  if [ $rc -ne 0 ]; then
    echo "pre-commit: GATE FAILED — $name" >&2
  fi
  return $rc
}

# both streams captured, shown (prefixed) only when the stage fails
quiet() {
  local name="$1"; shift
  local out rc=0
  out="$(mktemp)"
  run "$name" "$@" >"$out" 2>&1 || rc=$?
  if [ "$rc" -ne 0 ]; then
    sed "s/^/    $name: /" "$out" >&2
  fi
  rm -f "$out"
  return "$rc"
}

warm() {
  run "palette-cache" "${RUNNER[@]}" "$ROOT/make_schemes.py" --warm >/dev/null
}

case "$KIND" in
  selftest)
    [ -n "$SCRIPT" ] && [ -e "$ROOT/$SCRIPT" ] || usage
    NAME="$(basename "$SCRIPT" .py)"
    warm || exit 1
    if [ "$NAME" = "check_ebuild" ]; then
      quiet "selftest:$NAME" "${RUNNER[@]}" "$ROOT/$SCRIPT" --selftest
    else
      quiet "selftest:$NAME" \
        env -u GIT_INDEX_FILE -u GIT_DIR -u GIT_WORK_TREE -u GIT_PREFIX "${RUNNER[@]}" "$ROOT/$SCRIPT" --selftest
    fi
    ;;
  opa-test)
    quiet "opa-test" "${RUNNER[@]}" "$ROOT/scripts/opa_gate.py" --test
    ;;
  segment-lattice)
    quiet "segment-lattice" "${RUNNER[@]}" "$ROOT/segment_topology.py" --selftest
    ;;
  worklist|readme)
    warm || exit 1
    OUT="$(mktemp)"
    rc=0
    run "$KIND" "${RUNNER[@]}" "$ROOT/scripts/worklist_gate.py" --only "$KIND" >"$OUT" 2>&1 || rc=$?
    if [ "$rc" -ne 0 ]; then
      sed "s/^/    $KIND: /" "$OUT" >&2
      echo "    (run: python3 scripts/worklist_gate.py --only $KIND — it names each undischarged claim)" >&2
    fi
    rm -f "$OUT"
    exit "$rc"
    ;;
  *)
    usage
    ;;
esac
