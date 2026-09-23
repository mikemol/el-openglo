#!/usr/bin/env python3
"""qml_sanity.py — does the staged QML actually parse? (⊕QML-SANITY, rebuilt W25)

⚑ "CONTAINS THE STRING" IS NOT "PARSES".  A doubled-quote colour shipped a black
wallpaper in 1.23.0 while every string-presence check stayed green; the closure
(COTYPE.md:4318) put Qt's own linter in the build. That module did not survive
the recovery and make_deb printed a SKIP for it until 2026-09-21. This is it
again, on the qmllint this host ships (/usr/lib64/qt6/bin — no Python Qt
bindings are installed), with the KDE import path so `org.kde.*` resolves.

    qml_sanity.check_qml(text, label) -> [error strings]      # make_deb's contract
    qml_sanity.py <file.qml> ...                             # lint files; exit 1 on errors
    qml_sanity.py --selftest

Only ERRORS fail: syntax, unresolved types when the module IS on the path, a
property that does not exist. Warnings (unused imports, unqualified access —
qmllint's style opinions) are not. A missing qmllint is a SKIP, printed and
returned as no errors, because "not confirmed is not failed" — and the caller
sees the SKIP on stderr.

⚑ THE RENDER HALF (⊕RENDER-GATE) is scripts/render_qml.py: `render_nonempty`
here delegates to it for the two surfaces it can render, so make_deb runs both
"parses" and "draws" as the closure at :4545 said it would.
"""
import os
import shutil
import sys
import tempfile

import qt_sandbox as QT

ROOT = os.path.dirname(os.path.abspath(__file__))
QMLLINT = QT.QMLLINT
IMPORTS = ("/usr/lib64/qt6/qml",)
# diagnostic ids that are ERRORS for a shipped document (qmllint's own ids);
# `unqualified`, `unused-imports`, `import` and `missing-property` are context
# qmllint cannot see (Plasma injects `plasmoid`/`wallpaper`) and are not gated
ERROR_IDS = frozenset({"syntax", "duplicate-property-binding", "duplicate-bindings",
                       "top-level-component", "uncreatable-type", "inheritance-cycle"})


def _qmllint():
    return QMLLINT if os.path.exists(QMLLINT) else shutil.which("qmllint")


def check_qml(text, label="<qml>"):
    """[error strings] from qmllint over `text`; [] when clean or when qmllint is absent (SKIP)."""
    exe = _qmllint()
    if not exe:
        print(f"qml_sanity: SKIP {label} — qmllint not installed", file=sys.stderr)
        return []
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, os.path.basename(label) if label.endswith(".qml") else "subject.qml")
        open(p, "w", encoding="utf-8").write(text)
        cmd = [exe, "--json", "-"]
        for imp in IMPORTS:
            cmd += ["-I", imp]
        cmd.append(p)
        r = QT.run(cmd, capture_output=True, text=True)
    errs = []
    try:
        import json
        rep = json.loads(r.stdout)
        # ⚑ qmllint's per-file `success` flips on ANY diagnostic, and a Plasma
        # surface always carries some: `wallpaper` and `plasmoid` are context
        # properties the shell injects, which qmllint reports as "unqualified"
        # access. The ERROR ids are the ones a real app would refuse — a syntax
        # error is `id: syntax`, typed "warning" all the same (measured 2026-09-21
        # on a doubled-quote colour). Gate on the id, not the type or the flag.
        for f in rep.get("files", []):
            for w in f.get("warnings", []):
                if w.get("id") in ERROR_IDS or w.get("type") == "critical":
                    errs.append(f"{label}:{w.get('line')}:{w.get('column')}: "
                                f"[{w.get('id')}] {w.get('message')}")
    except (ValueError, KeyError):
        # no JSON at all is a tooling fault, and a tooling fault must be loud:
        # a linter that silently said nothing is the string-presence proxy again
        errs.append(f"{label}: qmllint produced no JSON (rc={r.returncode}): "
                    f"{(r.stderr or r.stdout).strip()[:300]}")
    return errs


def render_nonempty(surface, variant="EL-Openglo", min_lit=20):
    """(ok, detail): the emitted surface draws lit pixels headless (scripts/render_qml)."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import render_qml as RQ
    if not os.path.exists(RQ.QML):
        return True, f"SKIP render — {RQ.QML} not installed"
    if os.environ.get("SANDBOX_ON") == "1":
        # ⚑ QT'S OFFSCREEN PLATFORM OPENS THE GPU DEVICE EVEN ON THE SOFTWARE
        # SCENE GRAPH, and under sys-apps/sandbox that is a VIOLATION that fails
        # the whole staging (measured 2026-09-21: open_wr /dev/nvidiactl). A
        # build sandbox is where this gate cannot run; it runs everywhere else
        # (the pre-commit selftests, check_ebuild's caller, a developer's stage).
        return True, f"SKIP {surface}: a build sandbox forbids the GPU device the qml runner opens"
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "r.png")
        rc, err = RQ.render(surface, variant, 400, 48 if surface == "clock" else 200, out)
        if not os.path.exists(out):
            # ⚑ NO PICTURE AT ALL is the RUNNER failing (no scene graph under a
            # build sandbox, no GL) — a fact about the machine, so a SKIP, printed.
            # A picture with no lit pixels is the DEFECT, and fails below.
            print(f"qml_sanity: SKIP render-gate {surface} — the qml runner produced no "
                  f"image (rc={rc}): {err[-160:]}", file=sys.stderr)
            return True, f"SKIP {surface}: no image from the runner"
        n = RQ.pixels(out, variant)
    return n["lit"] >= min_lit, f"{surface}: {n['lit']} lit px (min {min_lit})"


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    if not _qmllint():
        print("  SKIP qmllint arms — not installed")
    else:
        chk("a clean document has no errors", check_qml("import QtQuick\nItem { width: 10 }\n", "ok.qml"), [])
        chk("a syntax error is an error", check_qml("import QtQuick\nItem { width: }\n", "bad.qml") != [], True)
        chk("a doubled-quote colour is an error (1.23.0's defect)",
            check_qml('import QtQuick\nRectangle { color: ""#000"" }\n', "quote.qml") != [], True)
        chk("a style warning is NOT an error",
            check_qml("import QtQuick\nimport QtQuick.Layouts\nItem { }\n", "warn.qml"), [])
        chk("a Plasma context property (wallpaper/plasmoid) is NOT an error",
            check_qml("import QtQuick\nItem { property bool b: wallpaper.configuration.breathe }\n",
                      "ctx.qml"), [])
    ok_r, detail = render_nonempty("clock")
    chk(f"the clock renders non-empty ({detail})", ok_r, True)
    print("qml_sanity selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    errs = []
    for p in sys.argv[1:]:
        errs += check_qml(open(p, encoding="utf-8").read(), p)
    for e in errs:
        print(e, file=sys.stderr)
    print(f"qml_sanity: {len(errs)} error(s) over {len(sys.argv) - 1} file(s)")
    sys.exit(1 if errs else 0)
