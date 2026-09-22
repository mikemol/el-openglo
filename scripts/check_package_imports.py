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

So this renders each package to a temp tree the way its emitter does, and asks:
for every `Name {` the emitted QML instantiates, is `Name.qml` in that tree (or a
type the imported modules supply)?

    scripts/check_package_imports.py             # per package, n of m resolved
    scripts/check_package_imports.py --json      # the measurement
    scripts/check_package_imports.py --selftest  # a missing companion is seen

WEAKNESS: the "type the modules supply" set is a NAMED LIST (QtQuick, Plasma,
Kirigami and friends), not a read of the QML type registry — a package that
instantiates a real module type this list does not know is reported as missing,
which is a false alarm, not a false all-clear. The direction of the error is the
safe one and it is stated.
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

# types the imported QML modules supply — QtQuick and the KDE/Plasma set this
# repo imports. A name here is NOT expected as a file beside the document.
PROVIDED = {
    # QtQuick & friends
    "Item", "Rectangle", "Text", "TextInput", "Image", "Canvas", "Repeater", "Row", "Column",
    "Grid", "Flow", "ListView", "ListModel", "ListElement", "Loader", "Timer", "MouseArea",
    "QtObject", "Component", "Connections", "Binding", "Window", "Shape", "ShapePath",
    "PathLine", "PathArc", "MultiEffect", "Behavior", "State", "Transition",
    "NumberAnimation", "ColorAnimation", "PropertyAnimation", "SequentialAnimation",
    "ParallelAnimation", "PauseAnimation", "RotationAnimation", "SpringAnimation",
    "HoverHandler", "TapHandler", "DragHandler", "PointHandler", "WheelHandler",
    "Gradient", "GradientStop", "LinearGradient", "Scale", "Rotation", "Translate",
    # Plasma / KDE
    "PlasmoidItem", "WallpaperItem", "ConfigModel", "ConfigCategory", "Dialog",
    "PlasmaCore", "SimpleKCM", "FormLayout", "CheckBox", "Slider", "SpinBox", "TextField",
    "Label", "Button", "ComboBox", "ScrollView", "Notifications", "StubRegistry",
}
INSTANTIATION = re.compile(r"(?<![\w.])([A-Z]\w*)\s*\{", re.M)


def package_facts(label, module_name, attr):
    """{label, files, instantiated, missing} — rendered the way the emitter does."""
    import importlib
    mod = importlib.import_module(module_name)
    with tempfile.TemporaryDirectory() as td:
        getattr(mod, attr)(td)
        docs, files = {}, set()
        for base, _dirs, names in os.walk(td):
            for n in names:
                files.add(n)
                if n.endswith(".qml"):
                    docs[n] = open(os.path.join(base, n), encoding="utf-8").read()
        want = set()
        for text in docs.values():
            want |= set(INSTANTIATION.findall(text))
        # a document's OWN component blocks (`component Foo:`) are local types
        local = set()
        for text in docs.values():
            local |= set(re.findall(r"(?m)^\s*component\s+(\w+)\s*:", text))
        want -= PROVIDED | local
        missing = sorted(n for n in want if f"{n}.qml" not in files)
    return {"package": label, "files": sorted(files), "instantiated": sorted(want),
            "missing": missing}


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
    bad = [p for p in m["packages"] if p["missing"]]
    for p in m["packages"]:
        n = len(p["instantiated"])
        print(f"  {p['package']:24s} {n - len(p['missing'])} of {n} instantiated types ship in the package"
              + (f" — MISSING {p['missing']}" if p["missing"] else ""))
    if bad:
        print(f"check_package_imports: REFUSED — {len(bad)} of {len(m['packages'])} packages would fail to load",
              file=sys.stderr)
        return 1
    print(f"check_package_imports: {len(m['packages'])} of {len(m['packages'])} packages ship every component they instantiate")
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
    chk("a mount without its display is seen",
        package_facts("broken", "_fake_pkg", "render_broken")["missing"], ["SegmentChar"])
    chk("...and a whole package is clean",
        package_facts("whole", "_fake_pkg", "render_whole")["missing"], [])
    chk("a module-provided type is not expected as a file",
        "Rectangle" in package_facts("whole", "_fake_pkg", "render_whole")["instantiated"], False)
    print("check_package_imports selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
