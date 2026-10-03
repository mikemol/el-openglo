#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_chrome_zips.py — are the Chrome store zips there, and are they what the Web Store takes? (W134)

    scripts/check_chrome_zips.py            # the verdict, as opa_gate chrome_zips decides it
    scripts/check_chrome_zips.py --json     # the measurement policy/chrome_zips.rego decides
    scripts/check_chrome_zips.py --selftest # the measurement can SEE a bad zip

The MEASUREMENT only: per expected variant, whether dist/chrome/<variant>.zip exists,
whether manifest.json sits at its root, whether it parses, and its manifest_version.
The requirement (six zips, each root-manifest v3) lives in policy/chrome_zips.rego.
A missing dist/ is not a defect of the THEME: it means publish_browsers --chrome has
not run here, and the policy withholds rather than denies.

WEAKNESS: this reads the zips; it does not ask the Web Store to validate them.
"""
import json
import os
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from publish_browsers import DEFAULT_OUT, VARIANTS


def measure(out=DEFAULT_OUT, variants=VARIANTS):
    d = os.path.join(out, "chrome")
    cases = []
    for v in variants:
        p = os.path.join(d, f"{v}.zip")
        c = {"variant": v, "exists": os.path.isfile(p), "root_manifest": None,
             "parses": None, "manifest_version": None}
        if c["exists"]:
            try:
                z = zipfile.ZipFile(p)
                c["root_manifest"] = "manifest.json" in z.namelist()
                if c["root_manifest"]:
                    try:
                        m = json.loads(z.read("manifest.json"))
                        c["parses"] = True
                        c["manifest_version"] = m.get("manifest_version")
                    except ValueError:
                        c["parses"] = False
            except zipfile.BadZipFile:
                c["root_manifest"] = False
        cases.append(c)
    return {"dist": os.path.isdir(d), "cases": cases}


def main(argv):
    known = {"--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_chrome_zips: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate
    return opa_gate.gate("chrome_zips")


def _selftest():
    """The measurement SEES each defect it reports: a manifest nested in a folder, a
    zip that is not a zip, a missing zip, and a good one."""
    ok = True
    with tempfile.TemporaryDirectory() as td:
        cd = os.path.join(td, "chrome")
        os.makedirs(cd)
        with zipfile.ZipFile(os.path.join(cd, "good.zip"), "w") as z:
            z.writestr("manifest.json", '{"manifest_version": 3}')
        with zipfile.ZipFile(os.path.join(cd, "nested.zip"), "w") as z:
            z.writestr("good/manifest.json", '{"manifest_version": 3}')
        with open(os.path.join(cd, "junk.zip"), "wb") as fh:
            fh.write(b"not a zip")
        got = {c["variant"]: c for c in measure(td, ("good", "nested", "junk", "absent"))["cases"]}
        for label, want in (("a good zip reads root manifest v3", (got["good"]["root_manifest"], got["good"]["manifest_version"]) == (True, 3)),
                            ("a nested manifest is SEEN as not at the root", got["nested"]["root_manifest"] is False),
                            ("a non-zip is SEEN, not crashed on", got["junk"]["root_manifest"] is False),
                            ("a missing zip is SEEN as absent", got["absent"]["exists"] is False)):
            print(f"  {'ok  ' if want else 'FAIL'} {label}")
            ok = ok and want
    print("check_chrome_zips selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv))
