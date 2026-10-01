#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""publish_browsers.py — build the store packages for the browser themes (W41).

    scripts/publish_browsers.py --chrome [--out DIR]   # dist/chrome/<variant>.zip, one per variant
    scripts/publish_browsers.py --selftest

⚑ NOTHING HERE DRAWS A THEME.  The Chrome manifests come from make_chrome.render_all,
the SAME authority make_deb stages at usr/share/el-openglo/chrome/<variant> (W134);
this script only packages what that emitter writes. A second theme builder here would
drift from the palette the moment it is re-solved (CLAUDE.md, check_token_source).

The Web Store wants manifest.json at the ZIP ROOT, not inside a folder: each zip is
the variant directory's CONTENTS. The zips are build output (dist/ is ignored); the
measurement of them is scripts/check_chrome_zips.py --json, judged by
policy/chrome_zips.rego through scripts/opa_gate.py chrome_zips.

WEAKNESS: this packages; it does not upload. The listing is W137 (operator's Web
Store account), and no store-side validation runs here.
"""
import os
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
DEFAULT_OUT = os.path.join(ROOT, "dist")
VARIANTS = ("EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit", "EL-Amber", "EL-Amber-Lit")


def zip_dir(src, dest):
    """Zip the CONTENTS of `src` into `dest` (so src/manifest.json is at the zip root).
    Entries are sorted and timestamps fixed, so the same input gives the same bytes."""
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".tmp"
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        # `src` is one variant's staging dir make_chrome.render_all just wrote, never the repo tree
        # population: a private TemporaryDirectory (or a selftest fixture), bounded by construction
        for base, dirs, files in os.walk(src):
            dirs.sort()
            for f in sorted(files):
                p = os.path.join(base, f)
                info = zipfile.ZipInfo(os.path.relpath(p, src), date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                with open(p, "rb") as fh:
                    z.writestr(info, fh.read())
    os.replace(tmp, dest)
    return dest


def build_chrome(out=DEFAULT_OUT, variants=VARIANTS):
    """Emit each variant through make_chrome into private staging, zip it; [zip paths]."""
    os.chdir(ROOT)
    import make_chrome
    with tempfile.TemporaryDirectory(prefix="el-chrome-") as td:
        dirs = {v: os.path.join(td, v) for v in variants}
        make_chrome.render_all(variants, dirs)
        return [zip_dir(dirs[v], os.path.join(out, "chrome", f"{v}.zip")) for v in variants]


def main(argv):
    known = {"--chrome", "--out", "--selftest"}
    args = argv[1:]
    for i, a in enumerate(args):
        if a.startswith("--") and a not in known:
            print(f"publish_browsers: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in args:
        return 0 if _selftest() else 1
    if "--chrome" not in args:
        print("publish_browsers: name a target: --chrome", file=sys.stderr)
        return 2
    out = args[args.index("--out") + 1] if "--out" in args else DEFAULT_OUT
    zips = build_chrome(out)
    print(f"publish_browsers: {len(zips)} of {len(VARIANTS)} Chrome zips -> {os.path.join(out, 'chrome')}")
    return 0 if len(zips) == len(VARIANTS) else 1


def _selftest():
    """The packager puts manifest.json at the ZIP ROOT and is deterministic."""
    ok = True
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "v")
        os.makedirs(os.path.join(src, "images"))
        open(os.path.join(src, "manifest.json"), "w").write('{"manifest_version": 3}')
        open(os.path.join(src, "images", "a.png"), "wb").write(b"x")
        a = zip_dir(src, os.path.join(td, "out", "a.zip"))
        b = zip_dir(src, os.path.join(td, "out", "b.zip"))
        names = sorted(zipfile.ZipFile(a).namelist())
        root = names == ["images/a.png", "manifest.json"]
        print(f"  {'ok  ' if root else 'FAIL'} manifest.json sits at the zip root (got {names})")
        same = open(a, "rb").read() == open(b, "rb").read()
        print(f"  {'ok  ' if same else 'FAIL'} the same input gives byte-identical zips")
        ok = root and same
    print("publish_browsers selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv))
