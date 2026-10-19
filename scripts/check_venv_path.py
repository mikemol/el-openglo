#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_venv_path.py - where the gate's python environment lives (W698, under W677).

Three gate-stage files read `ROOT/.venv` directly (check_routes for the hook console scripts,
worklist_gate for its re-exec under uv, check_closure for the witness tree's symlink), so a
`uv sync` (a repin) swaps the tools under a gate in flight. `venv(root)` is the one place that
names it: the directory EL_VENV points at when it is set (the snapshot venv gate/stage.sh
builds, W699), else `root/.venv` as before.

    scripts/check_venv_path.py --selftest

WEAKNESS. This only NAMES the directory. It does not check that the directory holds a working
environment, and a file that still joins `.venv` itself is not seen by it. The three files above
were found with `mikemol-pycodemod shapes` over scripts/; no check yet fails on a fourth.
"""

import os
import sys


def venv(root, environ=None):
    """The environment directory: EL_VENV when set and non-empty, else `root/.venv`."""
    env = os.environ if environ is None else environ
    return env.get("EL_VENV") or os.path.join(root, ".venv")


def _selftest():
    ok = True

    def chk(label: str, got: object, want: object) -> None:
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    chk("unset: the repo's own .venv", venv("/r", {}), "/r/.venv")
    chk("an empty EL_VENV is unset", venv("/r", {"EL_VENV": ""}), "/r/.venv")
    chk("EL_VENV wins over the repo", venv("/r", {"EL_VENV": "/s/v"}), "/s/v")
    chk(
        "the live environment is read when none is given",
        venv("/r"),
        os.environ.get("EL_VENV") or "/r/.venv",
    )
    print("venv_path selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if _selftest() else 1)
    print(f"venv_path: unknown arguments {sys.argv[1:]!r}", file=sys.stderr)
    sys.exit(2)
