# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""One bazel test per gate stage (W491, under W489 / W457).

gate/stage.sh runs ONE stage; this declares it as a test target, so each stage has its own log and
verdict in BuildBuddy and a flake names the stage that flaked (W454). //:precommit (BUILD.bazel) is a
test_suite over every stage, so `.githooks/pre-commit` still runs `bazel test //:precommit` and nothing
else.

⚑ THIS IS THE HOST TIER AND ITS TAGS SAY SO, exactly as the single target's did: the stages read the
working tree and the host's tools (opa, the qml runner, the paperkit engine, the warm palette cache),
none a declared input yet, so a stage is neither sandboxed (`no-sandbox`, `local`) nor served from cache
(`external`), and `exclusive` keeps two stages off the one working tree and the one ledger. W458 declares
each check's real closure, W459 gates the STAGED tree: each subtracts a tag.
"""

HOST_TIER = ["exclusive", "external", "local", "no-sandbox"]

def closure_data(closures, key):
    """A stage's data: its observed closure (closures.bzl) plus MODULE.bazel, which locates the checkout,
    deduplicated and sorted. A key with no closure is a KeyError at analysis: loud, never a quiet gap."""
    return sorted({p: True for p in closures[key] + ["MODULE.bazel"]}.keys())

def precommit_stage(name, args, data):
    """A gate stage as a host-tier test.

    Args:
        name: the target name.
        args: gate/stage.sh's arguments (KIND [SCRIPT]).
        data: the NAMED input files (select_tracked names; never a glob, never a directory).
    """
    native.sh_test(
        name = name,
        srcs = ["gate/stage.sh"],
        args = args,
        data = data,
        tags = HOST_TIER,
        # a generous ceiling, not a tight one: wall time is load, never a verdict (operator 2026-09-24)
        timeout = "eternal",
        size = "enormous",
    )
