#!/usr/bin/env python3
"""check_package_imports.py — every component a package INSTANTIATES ships in it.

⚑ WHY (measured LIVE, 2026-09-22, s134). The live wallpaper was ported onto the
shared segment display and the operator's shell said:

    Error loading the wallpaper ... main.qml:105:13: SegmentChar is not a type

QML resolves a bare-name component from the emitted file's OWN DIRECTORY, and
make_wallpaper_live.render_all wrote main.qml without SegmentChar.qml beside it.
Nothing caught it: every other gate reads the emitted TEXT (parity, the lint, the
symbol witnesses), and the text was perfect — the defect was in the DIRECTORY.
A rendered picture would not have caught it either; render_qml gained its own
companion list the same day, which is the same bug in the harness.

So this renders each package to a temp tree the way its emitter does and asks
QMLLINT, run with that tree's own ui directory on the import path, which types it
cannot resolve — the same resolution Plasma does, by the tool that owns it.

    scripts/check_package_imports.py             # per package, the unresolved types
    scripts/check_package_imports.py --json      # the measurement
    scripts/check_package_imports.py --selftest  # a missing companion is seen

⚑ THE EXIT CODE IS NOT THE ANSWER (measured s135): qmllint returns 0 whether or
not a type resolves — an unresolved type is a WARNING in the `[import]` category
("X was not found. Did you add all imports and dependencies?"). A gate reading
the status would pass a package that cannot load, which is this defect's own
shape one level up.

⚑ AND THIS REPLACED A HEURISTIC. The first version (s134) matched `Name {` and
compared against a hand-written list of types the QtQuick/Plasma modules supply —
an approximation that would have called a real module type "missing". qmllint
knows the type registry; the list is gone.

WEAKNESS: type RESOLUTION is not a load. A package whose types all resolve can
still fail at runtime (a binding loop, a missing config key, the plugin-id
mismatch that broke the desktop the FIRST time — W58 carries that half). This
says only that every type the QML names can be found where the package puts it.
"""
import json
import os
import re
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# (label, module, render_all attribute) — each emitter writes a whole package
PACKAGES = (
    ("org.el.segclock", "make_clock", "render_all"),
    ("org.el.openglo.live", "make_wallpaper_live", "render_all"),
    ("org.el.notifymarquee", "make_notify_marquee", "render_all"),
)

QMLLINT = "/usr/lib64/qt6/bin/qmllint"    # = qt_sandbox.QMLLINT; spawned only through it
# "X was not found. Did you add all imports and dependencies?" — the [import]
# category, which is what an unresolvable bare-name type reports as
UNRESOLVED = re.compile(r"^Warning: (\S+):(\d+):(\d+): (\w+) was not found\..*\[import\]", re.M)


def lint_tree(ui_dir, docs):
    """[{type, file, line}] for every type qmllint cannot resolve, with the tree's
    own ui directory on the import path — the resolution Plasma does."""
    import qt_sandbox as QT
    out = []
    for name in sorted(docs):
        r = QT.run([QMLLINT, "-I", ui_dir, os.path.join(ui_dir, name)],
                           capture_output=True, text=True, cwd=ui_dir, timeout=120)
        for m in UNRESOLVED.finditer(r.stdout + r.stderr):
            out.append({"type": m.group(4), "file": os.path.basename(m.group(1)),
                        "line": int(m.group(2))})
    return out


def package_facts(label, module_name, attr):
    """{label, files, missing} — rendered the way the emitter does, then linted."""
    import importlib
    mod = importlib.import_module(module_name)
    if not os.path.isfile(QMLLINT):
        return {"package": label, "withheld": f"{QMLLINT} is not on this host"}
    with tempfile.TemporaryDirectory() as td:
        getattr(mod, attr)(td)
        ui = os.path.join(td, "contents", "ui")
        # population: the package the emitter just rendered into this private tempdir
        files = sorted(n for base, _d, ns in os.walk(td) for n in ns)
        docs = [n for n in os.listdir(ui) if n.endswith(".qml")] if os.path.isdir(ui) else []
        missing = lint_tree(ui, docs) if docs else []
    return {"package": label, "files": files, "documents": sorted(docs), "missing": missing}


def measure(packages=PACKAGES):
    return {"packages": [package_facts(*p) for p in packages]}


def main(argv):
    known = {"--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_package_imports: unknown flag {a!r}", file=sys.stderr)
            return 2
    m = measure()
    if "--json" in argv:
        print(json.dumps(m, indent=1))
        return 0
    held = [p for p in m["packages"] if p.get("withheld")]
    bad = [p for p in m["packages"] if p.get("missing")]
    for p in m["packages"]:
        if p.get("withheld"):
            print(f"  {p['package']:24s} SKIP — {p['withheld']}")
            continue
        print(f"  {p['package']:24s} {len(p['documents'])} document(s), "
              + ("every type resolves" if not p["missing"] else "UNRESOLVED:"))
        for u in p["missing"]:
            print(f"        {u['type']} at {u['file']}:{u['line']} — not in the package")
    if bad:
        print(f"check_package_imports: REFUSED — {len(bad)} of {len(m['packages'])} packages would fail to load",
              file=sys.stderr)
        return 1
    if held:
        print(f"check_package_imports: SKIP — {len(held)} of {len(m['packages'])} packages unmeasured (no qmllint)",
              file=sys.stderr)
        return 0
    print(f"check_package_imports: {len(m['packages'])} of {len(m['packages'])} packages resolve every type they name")
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    # ⚑ THE MEASUREMENT CAN SEE: a package whose emitter writes the mount and not
    # the display — the live defect of s134, reproduced in a fixture
    def render_broken(d):
        os.makedirs(os.path.join(d, "contents", "ui"), exist_ok=True)
        open(os.path.join(d, "contents", "ui", "main.qml"), "w").write(
            "import QtQuick\nItem { SegmentChar { } Rectangle { } }\n")

    def render_whole(d):
        render_broken(d)
        open(os.path.join(d, "contents", "ui", "SegmentChar.qml"), "w").write("import QtQuick\nItem { }\n")

    import types
    fake = types.ModuleType("_fake_pkg")
    fake.render_broken, fake.render_whole = render_broken, render_whole
    sys.modules["_fake_pkg"] = fake
    broken = package_facts("broken", "_fake_pkg", "render_broken")
    whole = package_facts("whole", "_fake_pkg", "render_whole")
    if broken.get("withheld"):
        print(f"  SKIP — {broken['withheld']}; the resolution arms did not run")
    else:
        chk("a mount without its display is seen",
            [u["type"] for u in broken["missing"]], ["SegmentChar"])
        chk("...and it names where", (broken["missing"][0]["file"], broken["missing"][0]["line"]),
            ("main.qml", 2))
        chk("...and a whole package is clean", whole["missing"], [])
        # ⚑ a module type is resolved BY QMLLINT, not by a list this file keeps
        chk("a module-provided type needs no file beside the document",
            any(u["type"] == "Rectangle" for u in whole["missing"]), False)
    print("check_package_imports selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
