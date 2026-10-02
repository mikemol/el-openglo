#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_guest_recipe.py — the guest image recipe's pins, measured before anything is built (W235).

    scripts/check_guest_recipe.py            # the verdict, as opa_gate guest_recipe decides it
    scripts/check_guest_recipe.py --json     # the measurement policy/guest_recipe.rego decides
    scripts/check_guest_recipe.py --plan     # the mmdebstrap command the recipe resolves to
    scripts/check_guest_recipe.py --selftest # the measurement sees an unpinned snapshot and a live mirror

Reads oci/guest/recipe.json (catalog/guest-image.md (a)-(e)). Measures: whether the
snapshot is a pinned snapshot.debian.org timestamp (YYYYMMDDTHHMMSSZ, not `latest`,
not empty), whether the mirror resolves through that snapshot (a deb.debian.org or
any unpinned mirror makes the image unreproducible: the same recipe would build
different bytes tomorrow), whether the suite is the one the decisions name, and
whether the packages the decisions require are in the set and the absent set stays
out of it.

WEAKNESS: this checks the DECLARATION. It does not build the image, and it cannot
see whether the snapshot actually serves the packages (that is the build's first
fact); the absent set is checked against the declared list, not the installed
closure - customize.sh's dpkg-query output is where the closure is read.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
RECIPE = os.path.join(ROOT, "oci", "guest", "recipe.json")
PIN = re.compile(r"^\d{8}T\d{6}Z$")
SUITE = "trixie"                       # guest-image.md (a): the decided base
REQUIRED = ("kde-plasma-desktop", "sddm", "sddm-greeter-qt6", "plymouth", "jq")


def measure(recipe=None):
    if recipe is None:
        try:
            recipe = json.load(open(RECIPE, encoding="utf-8"))
        except (OSError, ValueError) as e:
            return {"cases": [], "withheld": [f"recipe unreadable: {e}"]}
    snap = recipe.get("snapshot")
    mirror = str(recipe.get("mirror", ""))
    pkgs = set(recipe.get("packages", [])) | set(recipe.get("boot", []))
    return {"cases": [{
        "recipe": "oci/guest/recipe.json",
        "snapshot": snap,
        "snapshot_pinned": isinstance(snap, str) and bool(PIN.match(snap)),
        "mirror_through_snapshot": mirror.startswith("https://snapshot.debian.org/archive/debian/")
                                   and "{snapshot}" in mirror,
        "suite": recipe.get("suite"),
        "want_suite": SUITE,
        "missing": sorted(set(REQUIRED) - pkgs),
        "forbidden_present": sorted(pkgs & set(recipe.get("absent", []))),
    }], "withheld": []}


def plan(recipe):
    """The mmdebstrap invocation the recipe resolves to (argv), with the snapshot filled in."""
    import calendar
    import time
    mirror = recipe["mirror"].format(snapshot=recipe["snapshot"])
    inc = ",".join(recipe["boot"] + recipe["packages"])
    epoch = calendar.timegm(time.strptime(recipe["snapshot"], "%Y%m%dT%H%M%SZ"))
    return (["env", f"SOURCE_DATE_EPOCH={epoch}", "mmdebstrap",
             f"--variant={recipe['variant']}", f"--include={inc}"]
            + (["--aptopt=APT::Install-Recommends \"false\""] if recipe.get("no_recommends") else [])
            + ["--customize-hook=sh oci/guest/customize.sh \"$1\" DEB SNAPSHOT GIT_REV",
               recipe["suite"], "guest.raw", mirror])


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    good = json.load(open(RECIPE, encoding="utf-8"))
    c = measure(good)["cases"][0]
    chk("the committed recipe is pinned, through the snapshot, nothing missing or forbidden",
        (c["snapshot_pinned"], c["mirror_through_snapshot"], c["missing"], c["forbidden_present"]), (True, True, [], []))
    for snap in ("latest", "", None, "2026-09-20"):
        chk(f"an unpinned snapshot {snap!r} is seen", measure(dict(good, snapshot=snap))["cases"][0]["snapshot_pinned"], False)
    chk("a live mirror is seen",
        measure(dict(good, mirror="http://deb.debian.org/debian"))["cases"][0]["mirror_through_snapshot"], False)
    chk("a forbidden package in the set is seen",
        measure(dict(good, packages=good["packages"] + ["python3"]))["cases"][0]["forbidden_present"], ["python3"])
    chk("the plan names the snapshot mirror", plan(good)[-1], f"https://snapshot.debian.org/archive/debian/{good['snapshot']}/")
    print("guest_recipe selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    for a in argv[1:]:
        if a not in {"--json", "--plan", "--selftest"}:
            print(f"guest_recipe: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    if "--plan" in argv:
        print(" ".join(plan(json.load(open(RECIPE, encoding="utf-8")))))
        return 0
    import opa_gate
    return opa_gate.gate("guest_recipe")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
