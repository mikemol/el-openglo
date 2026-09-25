#!/usr/bin/env python3
"""check_ebuild.py — the Gentoo overlay installs what the theme stages, and is an overlay.

⚑ THE CLAIM.  overlay/ is a Portage repository (the two marker files Portage
requires), its one ebuild is well-formed (pkgcheck when installed, else the
required variables and a bash parse), and its src_install — which is
`make_deb.py --stage "${D}"` — produces a NON-EMPTY tree in which every
destination make_deb.system_mapping() names exists. The last arm is the one
that matters: it runs the same function the ebuild runs, against a temp
DESTDIR, so "the ebuild installs the theme" is measured rather than asserted.

    scripts/check_ebuild.py            # the verdict, as opa_gate ebuild decides it
    scripts/check_ebuild.py --json     # the measurement policy/ebuild.rego decides
    scripts/check_ebuild.py --tree     # the staged install tree, one path per line
    scripts/check_ebuild.py --selftest

WEAKNESS, STATED.  This stages the INDEX tree under sys-apps/sandbox (writes
confined to a tempdir — Portage's own enforcement, run as the user) but with
THIS checkout's Python and deps, not the ebuild's BDEPEND. A dependency the
ebuild forgot to declare is invisible here (pkgcheck does not see it either);
only an actual `emerge` proves the BDEPEND set. What IS measured since
2026-09-21: every atom the ebuild DOES declare has a visible provider on this
host with the overlay in the repo set (deps_resolve). That still runs against
this host's repos — it cannot prove the overlay's carried colorspacious is
what resolves when ::guru is absent; the selftest asserts the carried ebuild
exists, which is the structural half of that. Staging is ~2 min cold (the
palette solve; the cache rides along) and seconds warm.

    scripts/check_ebuild.py --deps     # the declared atoms and whether each resolves
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


def bdepend_atoms(path=EBUILD):
    """The package atoms in BDEPEND / DEPEND / RDEPEND, USE-deps stripped."""
    text = open(path, encoding="utf-8").read()
    atoms = []
    for m in re.finditer(r'^(?:B|R)?DEPEND="([^"]*)"', text, re.M):
        for tok in m.group(1).split():
            tok = re.sub(r"\[.*?\]$", "", tok)
            if "/" in tok and not tok.startswith("$"):
                atoms.append(tok)
    return sorted(set(atoms))


def deps_resolve(path=EBUILD):
    """(ok, detail): every BDEPEND atom resolves to a visible package on THIS host,
    with the overlay itself in the repo set — so a dependency the overlay carries
    (dev-python/colorspacious, from ::guru) counts. Not on Gentoo → SKIP.

    ⚑ THIS ARM EXISTS BECAUSE THE WEAKNESS ABOVE WAS MEASURED: colorspacious
    resolved on luthen only because ::guru happened to be enabled; on any other
    host the ebuild would not merge. The overlay now carries it, and this asks
    Portage — not the checkout — whether each atom has a provider."""
    if not shutil.which("portageq"):
        return True, "SKIP deps-resolve (portageq not installed; not a Gentoo host)"
    atoms = bdepend_atoms(path)
    if not atoms:
        return False, "deps-resolve: the ebuild declares NO dependency atoms — the arm is vacuous"
    env = dict(os.environ, PORTDIR_OVERLAY=OVERLAY)
    unresolved = []
    for a in atoms:
        r = subprocess.run(["portageq", "best_visible", "/", a], env=env,
                           capture_output=True, text=True)
        if r.returncode != 0 or not r.stdout.strip():
            unresolved.append(a)
    if unresolved:
        return False, f"deps-resolve: {len(unresolved)} of {len(atoms)} atom(s) have no visible provider: " + ", ".join(unresolved)
    return True, f"deps-resolve: {len(atoms)} of {len(atoms)} atoms have a visible provider"


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
    # ⚑ THE WORK DIR IS UNDER THE REPO, NOT /tmp.  The staging runs with
    # SANDBOX_DENY=/tmp:/var/tmp (a build must not write shared temp), and DENY
    # covers reads too — a tempdir under /tmp would deny the clone itself.
    work = os.path.join(ROOT, ".ebuild-witness")
    os.makedirs(work, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=work) as td:
        if clean:
            # ⚑ THE INDEX, NOT HEAD.  Under the pre-commit hook the tree being
            # certified is what is STAGED; HEAD is the previous commit, and a
            # witness cloning HEAD refuses every fix to itself forever (measured:
            # the first commit of this very check). `git write-tree` is the
            # index as a tree object; outside a commit it equals HEAD's tree.
            src = os.path.join(td, "src")
            os.makedirs(src)
            sys.path.insert(0, os.path.join(ROOT, "scripts"))
            import git_tracked
            if git_tracked.source(ROOT) == "git":
                tree = subprocess.run(["git", "-C", ROOT, "write-tree"],
                                      capture_output=True, text=True, check=True).stdout.strip()
                archive = subprocess.run(["git", "-C", ROOT, "archive", "--format=tar", tree],
                                         capture_output=True, check=True).stdout
                subprocess.run(["tar", "-x", "-C", src], input=archive, check=True)
            else:
                # ⚑ NO .git (paperkit's Δ sandbox, R5 2026-09-25): there is no index to
                # write-tree, so @EBUILD graded `broken` there and could never be graded.
                # The tree is git_tracked's population — the same authority every other
                # population reads — copied file by file into the private src.
                for rel in git_tracked.files(root=ROOT):
                    s, d = os.path.join(ROOT, rel), os.path.join(src, rel)
                    if os.path.isfile(s):
                        os.makedirs(os.path.dirname(d), exist_ok=True)
                        shutil.copy2(s, d, follow_symlinks=False)  # atomic-write: exempt — into the private copy
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
        # ⚑ NOTHING MAY LAND OUTSIDE THE SOURCE TREE AND THE DESTDIR, AND THE
        # TOOL THAT ENFORCES IT IS PORTAGE'S OWN.  The first emerge of the fixed
        # tree died on `/tmp/EL-Openglo.colorscheme` — an emitter's __main__ demo
        # path staging ran needlessly. sys-apps/sandbox's `sandbox` binary is
        # what wraps every ebuild phase and it runs as any user: with
        # SANDBOX_WRITE limited to this tempdir, every other write is the same
        # EACCES the emerge produced. (A /tmp before/after snapshot was tried
        # first — racy against everything else on the box that touches /tmp.)
        # Without `sandbox` on PATH this arm is a counted SKIP, not a pass.
        env = dict(os.environ, TMPDIR=os.path.join(td, "tmp"))
        os.makedirs(env["TMPDIR"])
        cmd = [sys.executable, os.path.join(src, "make_deb.py"), "--stage", dest]
        sandboxed = shutil.which("sandbox") is not None
        if sandboxed:
            # ⚑ SANDBOX_WRITE ADDS; SANDBOX_DENY SUBTRACTS.  The default policy
            # (/etc/sandbox.conf) permits /tmp and /var/tmp, so the emerge's
            # EACCES on /tmp/EL-Openglo.colorscheme was plain Unix permissions
            # (a demo run had left it owned by the user; the build ran as
            # portage), not the sandbox. Either way a build must not write to
            # shared /tmp, and DENY is how this wrapper makes that a refusal.
            env.update(SANDBOX_WRITE=td, SANDBOX_DENY="/tmp:/var/tmp",
                       SANDBOX_PREDICT="", SANDBOX_VERBOSE="1")
            cmd = ["sandbox", "--"] + cmd
        r = subprocess.run(cmd, cwd=src, capture_output=True, text=True, env=env)
        if r.returncode != 0:
            raise RuntimeError(("make_deb --stage failed in a clean clone under sandbox: "
                                if sandboxed else "make_deb --stage failed in a clean clone: ")
                               + (r.stderr or r.stdout).strip()[-600:])
        globals()["_SANDBOX_NOTE"] = ("sandboxed (sys-apps/sandbox)" if sandboxed
                                      else "SKIP sandbox (not on PATH) — writes outside the tree unchecked")
        files = []
        # population: the staged DESTDIR inside this run's private workdir — build output, untracked by design
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


def lint_facts(path=EBUILD):
    """What linting the ebuild SAYS: which linter ran (pkgcheck, else a bash parse)
    and its output — no verdict. `pkgcheck` null means it is not installed here."""
    text = open(path, encoding="utf-8").read() if os.path.isfile(path) else ""
    out = {"present": os.path.isfile(path),
           "missing_vars": [v for v in REQUIRED_VARS if not re.search(rf"^{v}=", text, re.M)],
           "pkgcheck": None, "bash_parse": None}
    if not out["present"]:
        return out
    if shutil.which("pkgcheck"):
        r = subprocess.run(["pkgcheck", "scan", "--repo", OVERLAY, "-k", "error", path],
                           capture_output=True, text=True)
        out["pkgcheck"] = {"rc": r.returncode, "errors": "Error" in r.stdout,
                           "output": (r.stdout or r.stderr).strip()[:400]}
    r = subprocess.run(["bash", "-n", path], capture_output=True, text=True)
    out["bash_parse"] = {"rc": r.returncode, "stderr": r.stderr.strip()[:400]}
    return out


def deps_facts(path=EBUILD):
    """Per declared atom, whether Portage sees a provider — or `portageq: false`
    when this is not a Gentoo host (the atoms are still listed)."""
    atoms = bdepend_atoms(path) if os.path.isfile(path) else []
    if not shutil.which("portageq"):
        return {"portageq": False, "atoms": [{"atom": a, "resolves": None} for a in atoms]}
    env = dict(os.environ, PORTDIR_OVERLAY=OVERLAY)
    res = []
    for a in atoms:
        r = subprocess.run(["portageq", "best_visible", "/", a], env=env,
                           capture_output=True, text=True)
        res.append({"atom": a, "resolves": r.returncode == 0 and bool(r.stdout.strip())})
    return {"portageq": True, "atoms": res}


def staging_facts():
    """Stage from the index under sandbox (staged_tree) and report what came out:
    the error if it failed, else the file count, the mapped destinations absent,
    and whether sys-apps/sandbox confined it (false: writes outside unchecked)."""
    try:
        files, missing = staged_tree()
        return {"error": None, "files": len(files), "missing_dests": missing,
                "sandboxed": shutil.which("sandbox") is not None}
    except Exception as e:                                   # noqa: BLE001
        return {"error": f"{type(e).__name__}: {e}", "files": None, "missing_dests": None,
                "sandboxed": shutil.which("sandbox") is not None}


def measure():
    """The MEASUREMENT policy/ebuild.rego decides (W50). No arm judges itself:
    a missing linter, a non-Gentoo host, an absent sandbox are FACTS here, where
    they used to return (True, "SKIP ...") — an arm that passed by not running."""
    return {"markers": [{"path": p, "present": ok} for p, ok in overlay_markers()],
            "ebuild": lint_facts(), "deps": deps_facts(), "staging": staging_facts()}


def main(argv):
    known = {"--tree", "--selftest", "--deps", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_ebuild: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--deps" in argv:
        for a in bdepend_atoms():
            print(a)
        print(deps_resolve()[1])
        return 0
    if "--tree" in argv:
        files, _m = staged_tree()
        for f in files:
            print(f)
        return 0
    if "--json" in argv:
        import json
        print(json.dumps(measure(), indent=1))
        return 0
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import opa_gate
    return opa_gate.gate("ebuild")


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
        # the MEASUREMENT sees the same breakage as facts (policy/ebuild.rego rules on them)
        check("lint_facts reports the unparsable ebuild's bash rc", lint_facts(p)["bash_parse"]["rc"] != 0, True)
        open(p, "w").write('EAPI=8\nDESCRIPTION="x"\n')
        check("lint_facts names the unset variables",
              lint_facts(p)["missing_vars"], ["HOMEPAGE", "LICENSE", "SLOT", "EGIT_REPO_URI"])
    e_ok, e_detail = ebuild_wellformed()
    check(f"the real ebuild is well-formed ({e_detail[:60]})", e_ok, True)
    # ⚑ THE DEPS ARM MUST SEE AN ATOM NOBODY PROVIDES, and must refuse an
    # ebuild that declares none (a vacuous all-clear).
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "y-9999.ebuild")
        open(p, "w").write('EAPI=8\nBDEPEND="\n\tdev-python/numpy[${PYTHON_USEDEP}]\n'
                           '\tdev-nonesuch/el-openglo-selftest-absent\n"\n')
        check("atoms are read with USE-deps stripped", bdepend_atoms(p),
              ["dev-nonesuch/el-openglo-selftest-absent", "dev-python/numpy"])
        d_ok, d_detail = deps_resolve(p)
        if d_detail.startswith("SKIP"):
            print(f"  SKIP deps arms — {d_detail}")
        else:
            check("an atom with no provider is seen", d_ok, False)
            check("...and named", "el-openglo-selftest-absent" in d_detail, True)
            open(p, "w").write('EAPI=8\n')
            check("an ebuild with no atoms is refused, not passed", deps_resolve(p)[0], False)
            r_ok, r_detail = deps_resolve()
            check(f"the real ebuild's atoms all resolve ({r_detail})", r_ok, True)
            # the carried colorspacious is what makes that true WITHOUT ::guru
            check("the overlay carries dev-python/colorspacious",
                  os.path.isfile(os.path.join(OVERLAY, "dev-python", "colorspacious",
                                              "colorspacious-1.1.2.ebuild")), True)
    # ⚑ THE SANDBOX ARM MUST SEE A WRITE OUTSIDE THE TREE — the defect the second
    # emerge found. Run a planted script under the same wrapper and expect EACCES.
    if shutil.which("sandbox"):
        work = os.path.join(ROOT, ".ebuild-witness")
        os.makedirs(work, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=work) as td:
            env = dict(os.environ, SANDBOX_WRITE=td, SANDBOX_DENY="/tmp:/var/tmp",
                       SANDBOX_PREDICT="")
            r = subprocess.run(["sandbox", "--", sys.executable, "-c",
                                "open('/tmp/check_ebuild-selftest-leak', 'w').write('x')"],
                               capture_output=True, text=True, env=env)
            check("sandbox refuses a write to /tmp", r.returncode != 0, True)
            r = subprocess.run(["sandbox", "--", sys.executable, "-c",
                                f"open('{td}/ok', 'w').write('x')"],
                               capture_output=True, text=True, env=env)
            check("...and allows a write inside SANDBOX_WRITE", r.returncode, 0)
    else:
        print("  SKIP sandbox arms — sys-apps/sandbox not on PATH")
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
