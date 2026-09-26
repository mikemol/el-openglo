#!/usr/bin/env python3
"""check_deb.py — did the .deb build, does dpkg accept it, and does it carry what was staged? (W79)

⚑ THE REQUIREMENT IS policy/deb.rego; THIS IS THE MEASUREMENT. The pack is luthen's
checks/deb_pack.py (a digest-pinned Debian image on the host's BuildKit — this Gentoo
host has no dpkg): it writes OUTDIR/status ("<step> <code>" per step), info.txt,
contents.txt (dpkg-deb --contents) and prints a verdict JSON. This reads those back
beside the STAGED tree it packed (make_deb's DEB_ROOT) and reports, as facts:

  steps     each pack step and its exit code
  verdict   deb_pack's state / sha256 / epoch / base image
  staged    every regular file under the stage, DEBIAN/ excluded (what should ship)
  packed    every regular file dpkg-deb lists (what does ship)

    scripts/check_deb.py --json OUTDIR STAGE [VERDICT]
    scripts/check_deb.py --selftest
    scripts/opa_gate.py deb OUTDIR STAGE [VERDICT]   # measurement + policy, one verdict

WEAKNESS: it judges an ALREADY-PACKED directory — it does not run deb_pack (a
BuildKit build on md0 takes ~10 minutes, too heavy per commit), so a stale OUTDIR
beside a newer stage reads as missing files, not as staleness; the verdict's epoch
is reported so a caller can compare it to the stage's commit. contents.txt is
parsed by dpkg-deb's fixed `tar -tv` column layout (the path is the 6th field on).
"""
import json
import os
import sys


def parse_status(text):
    """{step: exit code} from deb_pack's status file."""
    out = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) == 2 and parts[1].lstrip("-").isdigit():
            out[parts[0]] = int(parts[1])
    return out


def parse_contents(text):
    """The regular files dpkg-deb --contents lists, as absolute install paths.
    A line is `mode owner size date time ./path` (directories end in '/', symlinks
    carry ' -> target'); only regular files ('-' mode) are kept."""
    out = []
    for line in text.splitlines():
        parts = line.split(None, 5)
        if len(parts) < 6 or not parts[0].startswith("-"):
            continue
        path = parts[5]
        out.append("/" + path[2:] if path.startswith("./") else path)
    return sorted(out)


def staged_files(stage):
    """Every regular file under the stage, DEBIAN/ excluded, as install paths."""
    out = []
    # population: the staged package root make_deb assembled — not the repo, so not git_tracked
    for dp, dirs, fs in os.walk(stage):
        rel = os.path.relpath(dp, stage)
        if rel == "DEBIAN" or rel.startswith("DEBIAN" + os.sep):
            continue
        for f in fs:
            p = os.path.join(dp, f)
            if os.path.isfile(p) and not os.path.islink(p):
                out.append("/" + os.path.normpath(os.path.relpath(p, stage)))
    return sorted(out)


def measure(outdir, stage, verdict_path=None):
    facts = {"outdir": outdir, "stage": stage, "withheld": []}
    status = os.path.join(outdir, "status")
    contents = os.path.join(outdir, "contents.txt")
    if not os.path.isfile(status) or not os.path.isfile(contents):
        facts["withheld"].append(f"no deb_pack output at {outdir} (status/contents.txt absent)")
        return facts
    if not os.path.isfile(os.path.join(stage, "DEBIAN", "control")):
        facts["withheld"].append(f"{stage} is not a package root (no DEBIAN/control)")
        return facts
    facts["steps"] = parse_status(open(status, encoding="utf-8").read())
    facts["packed"] = parse_contents(open(contents, encoding="utf-8").read())
    facts["staged"] = staged_files(stage)
    if verdict_path and os.path.isfile(verdict_path):
        facts["verdict"] = json.loads(open(verdict_path, encoding="utf-8").read())
    return facts


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} {label}: got {got!r}")

    chk("status lines parse to codes", parse_status("clamp 0\nbuild 2\n"), {"clamp": 0, "build": 2})
    listing = ("drwxr-xr-x root/root 0 2026-09-25 21:12 ./usr/\n"
               "-rw-r--r-- root/root 12 2026-09-25 21:12 ./usr/share/a b.txt\n"
               "lrwxrwxrwx root/root 0 2026-09-25 21:12 ./usr/bin/x -> y\n")
    chk("only regular files are packed paths (spaces kept)", parse_contents(listing), ["/usr/share/a b.txt"])
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "DEBIAN"))
        os.makedirs(os.path.join(td, "usr", "share"))
        open(os.path.join(td, "DEBIAN", "control"), "w").write("x")
        open(os.path.join(td, "usr", "share", "f"), "w").write("x")
        chk("the stage excludes DEBIAN/", staged_files(td), ["/usr/share/f"])
        chk("an absent pack output is WITHHELD", bool(measure(os.path.join(td, "none"), td)["withheld"]), True)
    print(f"check_deb selftest: {'PASS' if ok else 'FAIL'}")
    return ok


def main(argv):
    # operands are POSITIONAL (opa_gate passes bare operands through, never flags)
    args = argv[1:]
    known = {"--json", "--selftest"}
    for a in args:
        if a.startswith("--") and a not in known:
            print(f"check_deb: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in args:
        return 0 if _selftest() else 1
    rest = [a for a in args if not a.startswith("--")]
    if "--json" not in args or len(rest) not in (2, 3):
        print("usage: check_deb.py --json OUTDIR STAGE [VERDICT] | --selftest", file=sys.stderr)
        return 2
    print(json.dumps(measure(rest[0], rest[1], rest[2] if len(rest) == 3 else None), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
