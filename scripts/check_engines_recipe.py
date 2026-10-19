#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_engines_recipe.py - the engine image's pins, measured before anything is built (W257).

    scripts/check_engines_recipe.py            # the verdict, as opa_gate engines_recipe decides it
    scripts/check_engines_recipe.py --json     # the measurement policy/engines_recipe.rego decides
    scripts/check_engines_recipe.py --selftest # the measurement sees an unpinned snapshot and a live mirror

Reads oci/engines/Containerfile, the caller's Containerfile for luthen's self-serve runner
(luthen-observability:W328). Measures, in the shape of check_guest_recipe: whether the snapshot is a
pinned snapshot.debian.org timestamp, whether it is the SAME instant as oci/guest/recipe.json (one pin,
not two), whether apt reads through that snapshot and no live mirror, whether the install leaves recommends
out, whether Blender and a headless Godot are named, and whether the entrypoint prints both versions.

WEAKNESS. This checks the DECLARATION by reading the Containerfile text. It does not build the image and
cannot see that the snapshot serves the packages or that the names exist in trixie (they are unverified
until luthen's first run resolves them). The base image is a tag, not a digest: pinning it is a registry
lookup this host cannot make. The parse reads RUN lines joined at their backslash continuations; an install
built by a variable or a script is not seen.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
CONTAINERFILE = os.path.join(ROOT, "oci", "engines", "Containerfile")
GUEST = os.path.join(ROOT, "oci", "guest", "recipe.json")
PIN = re.compile(r"^\d{8}T\d{6}Z$")
SNAPSHOT_URL = re.compile(
    r"snapshot\.debian\.org/archive/debian/(?:%s|\$\{?SNAPSHOT\}?)/"
)
LIVE_MIRROR = re.compile(r"(?<!snapshot\.)debian\.org/debian")


def logical_lines(text):
    """The lines of `text` with backslash continuations joined."""
    return re.sub(r"\\\n\s*", " ", text).splitlines()


def installed(text):
    """([package names], whether every install leaves recommends out) over the apt-get install segments."""
    packages, clean = [], True
    for line in logical_lines(text):
        for seg in line.split("&&"):
            tokens = seg.split()
            if "apt-get" in tokens and "install" in tokens:
                rest = tokens[tokens.index("install") + 1 :]
                packages += [t for t in rest if not t.startswith("-")]
                clean = clean and "--no-install-recommends" in rest
    return packages, clean


def measure(text=None, guest_snapshot=None, path=CONTAINERFILE):
    if text is None:
        try:
            with open(path, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as e:
            return {"cases": [], "withheld": [f"Containerfile unreadable: {e}"]}
    if guest_snapshot is None:
        try:
            with open(GUEST, encoding="utf-8") as fh:
                guest_snapshot = json.load(fh).get("snapshot")
        except (OSError, ValueError) as e:
            return {"cases": [], "withheld": [f"guest recipe unreadable: {e}"]}
    arg = re.search(r"^ARG\s+SNAPSHOT=(\S+)", text, re.MULTILINE)
    snap = arg.group(1) if arg else None
    pkgs, clean = installed(text)
    entry = " ".join(
        ln for ln in logical_lines(text) if ln.startswith(("ENTRYPOINT", "CMD"))
    )
    return {
        "cases": [
            {
                "recipe": "oci/engines/Containerfile",
                "snapshot": snap,
                "snapshot_pinned": isinstance(snap, str) and bool(PIN.match(snap)),
                "guest_snapshot": guest_snapshot,
                "snapshot_is_guests": snap is not None and snap == guest_snapshot,
                "mirror_through_snapshot": bool(SNAPSHOT_URL.search(text))
                and not LIVE_MIRROR.search(text),
                "no_recommends": clean and bool(pkgs),
                "missing": sorted(
                    (["blender"] if "blender" not in pkgs else [])
                    + ([] if any(p.startswith("godot") for p in pkgs) else ["godot*"])
                ),
                "entry_prints_versions": "blender --version" in entry
                and bool(re.search(r"godot\S* --version", entry)),
            }
        ],
        "withheld": [],
    }


def _selftest():
    ok = True

    def chk(label: str, got: object, want: object) -> None:
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    with open(CONTAINERFILE, encoding="utf-8") as fh:
        good = fh.read()
    with open(GUEST, encoding="utf-8") as fh:
        pin = json.load(fh)["snapshot"]
    c = measure(good, pin)["cases"][0]
    chk(
        "the committed Containerfile is pinned to the guest snapshot, through it, complete",
        (
            c["snapshot_pinned"],
            c["snapshot_is_guests"],
            c["mirror_through_snapshot"],
            c["no_recommends"],
            c["missing"],
            c["entry_prints_versions"],
        ),
        (True, True, True, True, [], True),
    )
    for snap in ("latest", ""):
        bad = good.replace("ARG SNAPSHOT=" + pin, "ARG SNAPSHOT=" + snap)
        chk(
            f"an unpinned snapshot {snap!r} is seen",
            measure(bad, pin)["cases"][0]["snapshot_pinned"],
            False,
        )
    other = good.replace(pin, "20250101T000000Z")
    chk(
        "a pin that is not the guest's is seen",
        measure(other, pin)["cases"][0]["snapshot_is_guests"],
        False,
    )
    live = good.replace(
        "https://snapshot.debian.org/archive/debian/%s/",
        "http://deb.debian.org/debian",
    )
    chk(
        "a live mirror is seen",
        measure(live, pin)["cases"][0]["mirror_through_snapshot"],
        False,
    )
    chk(
        "an install that takes recommends is seen",
        measure(good.replace("--no-install-recommends ", ""), pin)["cases"][0][
            "no_recommends"
        ],
        False,
    )
    chk(
        "a missing engine package is named",
        measure(good.replace("godot3-server ", ""), pin)["cases"][0]["missing"],
        ["godot*"],
    )
    chk(
        "an entrypoint that does not print both versions is seen",
        measure(good.replace("godot3-server --version", "true"), pin)["cases"][0][
            "entry_prints_versions"
        ],
        False,
    )
    gone = measure(None, pin, path="/nonexistent/Containerfile")
    chk(
        "an unreadable Containerfile is withheld with no case, not an empty verdict",
        (gone["cases"], len(gone["withheld"])),
        ([], 1),
    )
    print("engines_recipe selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    for a in argv[1:]:
        if a not in {"--json", "--selftest"}:
            print(f"engines_recipe: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate

    return opa_gate.gate("engines_recipe")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
