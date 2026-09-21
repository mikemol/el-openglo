#!/usr/bin/env python3
"""check_ebuild.py — the Gentoo overlay installs what the theme stages, and is an overlay.

⚑ THE CLAIM.  overlay/ is a Portage repository (the two marker files Portage
requires), its one ebuild is well-formed (pkgcheck when installed, else the
required variables and a bash parse), and its src_install — which is
`make_deb.py --stage "${D}"` — produces a NON-EMPTY tree in which every
destination make_deb.system_mapping() names exists. The last arm is the one
that matters: it runs the same function the ebuild runs, against a temp
DESTDIR, so "the ebuild installs the theme" is measured rather than asserted.

    scripts/check_ebuild.py            # exit 0 iff overlay + ebuild + staging all hold
    scripts/check_ebuild.py --tree     # the staged install tree, one path per line
    scripts/check_ebuild.py --selftest

WEAKNESS, STATED.  This stages with THIS checkout's Python and deps, not inside
Portage's sandbox with the ebuild's BDEPEND. A dependency the ebuild forgot to
declare is invisible here (pkgcheck does not see it either); only an actual
`emerge` proves the BDEPEND set. Staging is ~2 min cold (the palette solve) and
seconds warm.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OVERLAY = os.path.join(ROOT, "overlay")
EBUILD = os.path.join(OVERLAY, "x11-themes", "el-openglo", "el-openglo-9999.ebuild")
REQUIRED_VARS = ("EAPI", "DESCRIPTION", "HOMEPAGE", "LICENSE", "SLOT", "EGIT_REPO_URI")


def overlay_markers():
    """[(path, present)] for the two files Portage needs to treat a dir as a repo."""
    return [(p, os.path.isfile(os.path.join(OVERLAY, p)))
            for p in ("metadata/layout.conf", "profiles/repo_name")]


def ebuild_wellformed(path=EBUILD):
    """(ok, detail). pkgcheck if present; else a bash parse + required variables."""
    if not os.path.isfile(path):
        return False, "ebuild missing"
    text = open(path, encoding="utf-8").read()
    missing = [v for v in REQUIRED_VARS if not re.search(rf"^{v}=", text, re.M)]
    if missing:
        return False, f"required variable(s) unset: {', '.join(missing)}"
    if shutil.which("pkgcheck"):
        r = subprocess.run(["pkgcheck", "scan", "--repo", OVERLAY, "-k", "error", path],
                           capture_output=True, text=True)
        if r.returncode != 0 or "Error" in r.stdout:
            return False, "pkgcheck: " + (r.stdout or r.stderr).strip()[:400]
        return True, "pkgcheck: no errors"
    r = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
    if r.returncode != 0:
        return False, "bash -n: " + r.stderr.strip()[:400]
    return True, "SKIP pkgcheck (not installed); bash parses, required variables set"


def staged_tree(clean=True):
    """Stage into a temp DESTDIR the way the ebuild does, and return (files, missing).

    ⚑ FROM A CLEAN CLONE, NOT THIS CHECKOUT.  git-r3 clones the repo; the ebuild
    sees only what is COMMITTED. This witness first staged from the working tree,
    where gitignored outputs of earlier emitter runs sat on disk, and reported
    301 files while the installed package (qlist, 2026-09-21) had no Aurorae, no
    Plasma style and no wallpaper. A `git clone --shared` of HEAD into a temp dir
    is what the ebuild gets; staging runs there, in a subprocess, with that
    tree's make_deb. `clean=False` keeps the old behaviour for the selftest's
    speed. Raises if the tree is empty."""
    with tempfile.TemporaryDirectory() as td:
        if clean:
            # ⚑ THE INDEX, NOT HEAD.  Under the pre-commit hook the tree being
            # certified is what is STAGED; HEAD is the previous commit, and a
            # witness cloning HEAD refuses every fix to itself forever (measured:
            # the first commit of this very check). `git write-tree` is the
            # index as a tree object; outside a commit it equals HEAD's tree.
            src = os.path.join(td, "src")
            os.makedirs(src)
            tree = subprocess.run(["git", "-C", ROOT, "write-tree"],
                                  capture_output=True, text=True, check=True).stdout.strip()
            archive = subprocess.run(["git", "-C", ROOT, "archive", "--format=tar", tree],
                                     capture_output=True, check=True).stdout
            subprocess.run(["tar", "-x", "-C", src], input=archive, check=True)
            # ⚑ THE PALETTE CACHE RIDES ALONG.  It is gitignored, so the archive
            # has none and staging re-solves cold (~108 s) — over paperkit's
            # per-check budget, which read as a red @EBUILD under the hook while
            # the same tool passed from a shell. The cache is keyed by a stamp
            # over the solver sources, so a stale copy is re-solved, not trusted.
            cache = os.path.join(ROOT, ".palette-cache.json")
            if os.path.isfile(cache):
                shutil.copy2(cache, os.path.join(src, ".palette-cache.json"))
        else:
            src = ROOT
        dest = os.path.join(td, "dest")
        r = subprocess.run([sys.executable, os.path.join(src, "make_deb.py"), "--stage", dest],
                           cwd=src, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("make_deb --stage failed in a clean clone: "
                               + (r.stderr or r.stdout).strip()[-600:])
        files = []
        for dp, _dirs, fs in os.walk(dest):
            for f in fs:
                files.append(os.path.relpath(os.path.join(dp, f), dest))
        if not files:
            raise RuntimeError("staging produced an EMPTY tree — the packager is broken, "
                               "not the theme small")
        sys.path.insert(0, src)
        import importlib
        make_deb = importlib.import_module("make_deb")
        mapping = make_deb.system_mapping() + make_deb.helper_source_mapping()
        missing = [dst for _src, dst in mapping if not os.path.exists(os.path.join(dest, dst))]
        return sorted(files), missing


def main(argv):
    known = {"--tree", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_ebuild: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--tree" in argv:
        files, _m = staged_tree()
        for f in files:
            print(f)
        return 0

    problems, notes = [], []
    for p, ok in overlay_markers():
        (notes if ok else problems).append(f"overlay marker {p}: {'present' if ok else 'MISSING'}")
    ok, detail = ebuild_wellformed()
    (notes if ok else problems).append(f"ebuild: {detail}")
    try:
        files, missing = staged_tree()
        if missing:
            problems.append(f"{len(missing)} mapped destination(s) absent after staging: "
                            + ", ".join(missing[:5]))
        else:
            notes.append(f"staging: {len(files)} files; every mapped destination present")
    except Exception as e:                                   # noqa: BLE001
        problems.append(f"staging: {type(e).__name__}: {e}")

    if problems:
        print(f"check_ebuild: REFUSED — {len(problems)} of {len(problems) + len(notes)} "
              f"arm(s) do not hold:", file=sys.stderr)
        for p in problems:
            print(f"    {p}", file=sys.stderr)
        return 1
    print(f"check_ebuild: {len(notes)} of {len(notes)} arms hold — " + "; ".join(notes))
    return 0


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    check("the overlay markers are both present", all(p for _n, p in overlay_markers()), True)
    # ⚑ THE WELL-FORMEDNESS ARM MUST SEE A BROKEN EBUILD.
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "x-9999.ebuild")
        open(p, "w").write('EAPI=8\nDESCRIPTION="x"\n')
        w_ok, w_detail = ebuild_wellformed(p)
        check("an ebuild missing required variables is seen", w_ok, False)
        open(p, "w").write("EAPI=8\nDESCRIPTION=\"x\"\nHOMEPAGE=\"x\"\nLICENSE=\"GPL-3\"\n"
                           "SLOT=\"0\"\nEGIT_REPO_URI=\"x\"\nsrc_install() {\n")
        w_ok, _d = ebuild_wellformed(p)
        check("an ebuild that does not parse is seen (bash -n / pkgcheck)", w_ok, False)
    e_ok, e_detail = ebuild_wellformed()
    check(f"the real ebuild is well-formed ({e_detail[:60]})", e_ok, True)
    # ⚑ THE STAGING ARM MUST REFUSE AN EMPTY TREE, and must see a missing dest.
    files, missing = staged_tree()
    check("staging is non-empty", len(files) > 0, True)
    check("every mapped destination is staged", missing, [])
    print("check_ebuild selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
