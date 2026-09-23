#!/usr/bin/env python3
"""check_root_helpers.py — MEASURE the root helpers against a SCRATCH root (W71a/W71b).

`el-openglo-plymouth` and `el-openglo-sddm` are the selection routes a user runs
with sudo (catalog/guest-image.md (d)); the guest image runs them in its chroot.
This runs both, as shipped in make_deb, against a throwaway root:

  * the real themes, rendered into <root>/usr/share by make_plymouth.render_all
    and make_sddm.render_all — the layout the helper must find;
  * EL_OPENGLO_ROOT=<root>, the seam each helper prefixes to every path it reads
    or writes, so nothing touches / ;
  * a PATH holding ONLY stubs (`id` answers 0; `update-alternatives`,
    `update-initramfs`, `plymouth-set-default-theme` log their argv and do what
    the real tool does to the root) plus the coreutils the helpers call — so a
    tool's ABSENCE is a scenario, not an accident of this machine.

    scripts/check_root_helpers.py --json      # the measurement (policy/root_helpers.rego decides)
    scripts/check_root_helpers.py --list      # one line per case
    scripts/check_root_helpers.py --selftest  # the measurement can SEE a failed run

⚑ A HELPER WITHOUT THE SEAM IS NEVER EXECUTED. It would write the real /etc; its
cases are WITHHELD, naming why.

WEAKNESS, STATED. The stubs model what the real tools do to the files; they do
not model dpkg's alternatives database, dracut, or initramfs contents. A helper
that passes here selects the right path; whether plymouth then DRAWS it at boot is
P3's question (guest-image.md), and needs the VM.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SEAM = 'R="${EL_OPENGLO_ROOT:-}"'
COREUTILS = ["cp", "cat", "mkdir", "rm", "readlink", "ln"]

STUBS = {
    "id": '#!/bin/sh\necho 0\n',
    "update-alternatives": r'''#!/bin/sh
echo "update-alternatives $*" >> "$EL_OPENGLO_ROOT/tool.log"
[ -n "${STUB_UA_FAIL:-}" ] && exit 2
if [ "$1" = "--set" ]; then
  mkdir -p "$EL_OPENGLO_ROOT/etc/alternatives"
  ln -sfn "$3" "$EL_OPENGLO_ROOT/etc/alternatives/$2"
fi
exit 0
''',
    "update-initramfs": '#!/bin/sh\necho "update-initramfs $*" >> "$EL_OPENGLO_ROOT/tool.log"\n',
    "plymouth-set-default-theme": '#!/bin/sh\necho "plymouth-set-default-theme $*" >> "$EL_OPENGLO_ROOT/tool.log"\n',
}

# (helper, scenario, argv, tools on PATH, env)
PLY_ALL = ["update-alternatives", "update-initramfs", "plymouth-set-default-theme"]
SCENARIOS = [
    ("el-openglo-plymouth", "happy", ["EL-Openglo"], PLY_ALL, {}),
    ("el-openglo-plymouth", "alternatives_fail", ["EL-Openglo"], PLY_ALL, {"STUB_UA_FAIL": "1"}),
    ("el-openglo-plymouth", "no_update_initramfs", ["EL-Openglo"], ["update-alternatives"], {}),
    ("el-openglo-plymouth", "no_initramfs_flag", ["--no-initramfs", "EL-Openglo"], ["update-alternatives"], {}),
    ("el-openglo-plymouth", "set_default_theme_route", ["EL-Openglo"], ["plymouth-set-default-theme"], {}),
    ("el-openglo-plymouth", "no_route", ["EL-Openglo"], [], {}),
    ("el-openglo-sddm", "theme", ["EL-Azure-Lit"], [], {}),
    ("el-openglo-sddm", "unknown_variant", ["EL-Nope"], [], {}),
    ("el-openglo-sddm", "breeze_after_theme", ["--breeze"], [], {}),
]


def _variants():
    import make_deb
    return list(make_deb.VARIANTS)


def plymouth_name(v):
    """The theme's directory name, from make_plymouth's authority when it has one."""
    import make_plymouth as MP
    return MP.theme_name(v) if hasattr(MP, "theme_name") else f"el-openglo-{v}"


def build_root(root):
    """Render the real plymouth + SDDM themes into root, plus a stock-breeze stand-in."""
    import make_plymouth as MP
    import make_sddm as SD
    vs = _variants()
    pthemes = os.path.join(root, "usr/share/plymouth/themes")
    MP.render_all(vs, {v: os.path.join(pthemes, plymouth_name(v)) for v in vs})
    SD.render_all(os.path.join(root, "usr/share/sddm/themes"), vs)
    os.makedirs(os.path.join(root, "usr/share/sddm/themes/breeze"), exist_ok=True)
    for v in vs:
        wp = os.path.join(root, f"usr/share/wallpapers/{v}/contents/images")
        os.makedirs(wp, exist_ok=True)
        open(os.path.join(wp, "1920x1080.png"), "wb").write(b"png")


def plymouth_layout(root):
    """Per variant: the dir, its .plymouth files, and whether the config's refs resolve."""
    import configparser
    out = []
    for v in _variants():
        name = plymouth_name(v)
        d = os.path.join(root, "usr/share/plymouth/themes", name)
        files = sorted(f for f in os.listdir(d) if f.endswith(".plymouth")) if os.path.isdir(d) else []
        refs = {}
        for f in files:
            cp = configparser.ConfigParser()
            cp.read(os.path.join(d, f))
            sf = cp.get("script", "ScriptFile", fallback="")
            idir = cp.get("script", "ImageDir", fallback="")
            refs[f] = {"script_file": sf, "script_exists": bool(sf) and os.path.isfile(root + sf),
                       "image_dir": idir, "image_dir_exists": bool(idir) and os.path.isdir(root + idir)}
        out.append({"kind": "layout", "variant": v, "dir": name, "plymouth_files": files, "refs": refs})
    return out


def _bindir(scratch, tools):
    b = os.path.join(scratch, "bin")
    os.makedirs(b)
    for c in COREUTILS:
        os.symlink(shutil.which(c), os.path.join(b, c))
    for t in ["id"] + tools:
        p = os.path.join(b, t)
        open(p, "w").write(STUBS[t])
        os.chmod(p, 0o755)
    return b


def _read_tree(root, rel):
    p = os.path.join(root, rel)
    if os.path.islink(p):
        return {"link": os.readlink(p)}
    if os.path.isfile(p):
        return {"text": open(p, encoding="utf-8", errors="replace").read()}
    return None


def run_case(helper, scenario, argv, tools, env, scripts, work):
    import make_sddm as SD
    body = scripts[helper]
    case = {"kind": "run", "helper": helper, "scenario": scenario, "argv": argv,
            "tools": tools}
    if SEAM not in body:
        case["withheld"] = f"{helper} has no EL_OPENGLO_ROOT seam; not executed (it would write /)"
        return case
    scratch = tempfile.mkdtemp(prefix=f"{scenario}-", dir=work)
    root = os.path.join(scratch, "root")
    shutil.copytree(os.path.join(work, "_themes"), root, symlinks=True)
    helper_p = os.path.join(scratch, helper)
    open(helper_p, "w").write(body)
    os.chmod(helper_p, 0o755)
    b = _bindir(scratch, tools)
    e = {"PATH": b, "EL_OPENGLO_ROOT": root, **env}

    def go(args):
        return subprocess.run(["/bin/sh", helper_p, *args], env=e, capture_output=True, text=True)

    if scenario == "breeze_after_theme":            # select the greeter first, then undo
        pre = go(["EL-Openglo"])
        case["pre_exit"] = pre.returncode
    r = go(argv)
    log = os.path.join(root, "tool.log")
    case.update({
        "exit": r.returncode, "stdout": r.stdout, "stderr": r.stderr,
        "tool_log": open(log).read().splitlines() if os.path.isfile(log) else [],
        "alternative": _read_tree(root, "etc/alternatives/default.plymouth"),
        "dropin": _read_tree(root, "etc/sddm.conf.d/el-openglo.conf"),
        "sddm_conf_written": os.path.exists(os.path.join(root, "etc/sddm.conf")),
    })
    if helper == "el-openglo-plymouth":
        n = plymouth_name(argv[-1])
        case["want_theme"] = f"/usr/share/plymouth/themes/{n}/{n}.plymouth"
        case["want_name"] = n
    else:
        v = argv[-1] if not argv[-1].startswith("--") else None
        case["want_current"] = SD.theme_id(v) if v and v in _variants() else None
        case["want_theme_dir_exists"] = bool(v) and os.path.isfile(
            os.path.join(root, "usr/share/sddm/themes", SD.theme_id(v), "metadata.desktop"))
    return case


def measure():
    import make_deb
    scripts = {"el-openglo-plymouth": make_deb.PLYMOUTH_HELPER,
               "el-openglo-sddm": make_deb.sddm_helper()}   # the table filled, as stage() writes it
    work = tempfile.mkdtemp(prefix="el-root-helpers-")
    try:
        themes = os.path.join(work, "_themes")
        build_root(themes)
        cases = plymouth_layout(themes)
        for sc in SCENARIOS:
            cases.append(run_case(*sc, scripts, work))
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return {"cases": cases}


def main(argv):
    known = {"--json", "--list", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_root_helpers: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    if "--list" in argv:
        m = measure()
        for c in m["cases"]:
            if c["kind"] == "layout":
                print(f"  layout  {c['dir']:28s} {c['plymouth_files']}")
            else:
                print(f"  run     {c['helper']:20s} {c['scenario']:24s} "
                      + (f"WITHHELD {c['withheld']}" if "withheld" in c else f"exit {c['exit']}"))
        runs = [c for c in m["cases"] if c["kind"] == "run"]
        print(f"\ncheck_root_helpers: {sum('withheld' not in c for c in runs)} of {len(runs)} "
              f"run(s) executed; {sum(c['kind'] == 'layout' for c in m['cases'])} layout(s) "
              "(the verdict: scripts/opa_gate.py root_helpers)")
        return 0
    print("usage: check_root_helpers.py --json | --list | --selftest  "
          "(the verdict: scripts/opa_gate.py root_helpers)", file=sys.stderr)
    return 2


def _selftest():
    """The measurement can SEE: a helper that exits 3 is measured as exit 3 with its
    stderr; a stub's argv reaches the log; a seamless helper is withheld, not run."""
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    work = tempfile.mkdtemp(prefix="el-root-helpers-st-")
    try:
        os.makedirs(os.path.join(work, "_themes"))
        bad = {"el-openglo-plymouth": f'#!/bin/sh\n{SEAM}\nupdate-initramfs -u\necho boom >&2\nexit 3\n',
               "el-openglo-sddm": '#!/bin/sh\nexit 0\n'}
        c = run_case("el-openglo-plymouth", "happy", ["EL-Openglo"], ["update-initramfs"], {}, bad, work)
        chk("a failing helper's exit is seen", c.get("exit"), 3)
        chk("its stderr is seen", c.get("stderr"), "boom\n")
        chk("a stub's argv reaches the log", c.get("tool_log"), ["update-initramfs -u"])
        s = run_case("el-openglo-sddm", "theme", ["EL-Azure-Lit"], [], {}, bad, work)
        chk("a helper with no seam is withheld, never run", "withheld" in s and "exit" not in s, True)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print("check_root_helpers selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv))
