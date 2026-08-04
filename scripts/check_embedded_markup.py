#!/usr/bin/env python3
"""check_embedded_markup.py — an ARTIFACT embedded in Python is un-previewable.

⚑ THE DEFECT.  A generator that builds SVG or QML by concatenating string
literals has hidden an artifact inside a program. Nobody can open it, no viewer
can render it, no diff shows which element changed, and no linter or schema
validator can reach it. The wallpaper was the extreme case: its entire SVG was
built at module level and written as an import side effect, so the only way to
SEE it was to run the module and read a file whose name it chose.

Markup belongs in files. A generator should read a TEMPLATE and substitute, so
the artifact is previewable at rest and the substitution is the only thing the
program owns.

    scripts/check_embedded_markup.py            # exit 0 iff no source embeds markup
    scripts/check_embedded_markup.py --report   # every embedding, with its size
    scripts/check_embedded_markup.py --waivers  # the accepted ones, and why

⚑ THIS MEASURES BY AST, NOT BY GREP.  A string containing `<svg` is found by
walking the module's constants — so a mention inside a COMMENT (this docstring
says `<svg` and must not fire) is invisible to it, and a literal assembled across
an implicit concatenation is still one constant. A regex over the source would
get both wrong in opposite directions.

⚑ AND SIZE IS THE DISCRIMINATOR, NOT PRESENCE.  A one-line `<rect/>` built in a
loop is a DRAWING PRIMITIVE — the program's proper business. A 40-line document
with a <defs> block and a filter chain is an ARTIFACT wearing a string's
clothes. The threshold is stated, not implied, so raising it is a visible act.
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A literal at or above this many lines is an artifact, not a primitive.
DOCUMENT_LINES = 8

# ⚑ THE KINDS THAT ARE ARTIFACTS RATHER THAN PROSE, BY MIME.
#
# This was a hand-written tuple of markers — ("<svg", "<?xml", "import QtQuick",
# …) — which is a worse libmagic that I maintain. scripts/identify.py owns the
# question now, backed by libmagic plus this repo's own signatures, so adding a
# kind means adding a SIGNATURE rather than remembering to edit a tuple here.
#
# Prose (text/plain) and Python are not artifacts; a payload identifying as one
# of these is a document that belongs in a file.
ARTIFACT_MIMES = (
    "text/x-qml",
    "image/svg+xml",
    "text/xml",
    "application/xml",
    "text/html",
    "text/x-kde-colorscheme",
    "text/x-konsole-colorscheme",
)

# Embeddings accepted with a stated reason. path -> why.
WAIVERS = {}


def embeddings(root=None, min_lines=DOCUMENT_LINES):
    """[(relpath, lineno, marker, n_lines)] — markup documents held in source."""
    root = root or ROOT
    out = []
    for fn in sorted(os.listdir(root)):
        if not fn.endswith(".py"):
            continue
        path = os.path.join(root, fn)
        try:
            tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            # A docstring is prose ABOUT markup, never markup. Skip the string
            # that sits first in a module/class/function body.
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                text = node.value
                n = text.count("\n") + 1
                if n < min_lines:
                    continue
                kind = _identify(text)
                if kind in ARTIFACT_MIMES:
                    out.append((fn, node.lineno, kind, n))
    return out


def _identify(text):
    """The MIME kind of a string payload, via the repo's identification tool."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    try:
        import identify
    except ImportError:
        return None
    return identify.of_string(text)


def _docstrings(tree):
    """Line numbers of every docstring constant, which are prose by definition."""
    lines = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None and node.body:
                first = node.body[0]
                if isinstance(first, ast.Expr):
                    lines.add(first.lineno)
    return lines


def findings(root=None, min_lines=DOCUMENT_LINES):
    """embeddings() minus docstrings — the ones that are genuinely artifacts."""
    root = root or ROOT
    out = []
    for fn, lineno, marker, n in embeddings(root, min_lines):
        path = os.path.join(root, fn)
        try:
            tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
        except SyntaxError:
            continue
        if lineno in _docstrings(tree):
            continue
        out.append((fn, lineno, marker, n))
    return out


def main(argv):
    known = {"--report", "--waivers"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_embedded_markup: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--waivers" in argv:
        for p, why in sorted(WAIVERS.items()):
            print(f"{p}\t{why}")
        return 0

    found = findings()
    if "--report" in argv:
        for fn, lineno, marker, n in found:
            mark = "waived" if fn in WAIVERS else "OPEN  "
            print(f"{mark}\t{fn}:{lineno}\t{marker}\t{n} lines")
        return 0

    unwaived = [f for f in found if f[0] not in WAIVERS]
    if unwaived:
        print(f"check_embedded_markup: REFUSED — {len(unwaived)} markup document(s) "
              f"embedded in source, un-previewable and un-lintable:", file=sys.stderr)
        for fn, lineno, marker, n in unwaived:
            print(f"    {fn}:{lineno}  {marker}  {n} lines", file=sys.stderr)
        print(f"    Move each to a template file the generator READS.",
              file=sys.stderr)
        print(f"  fixes: {len(unwaived)}", file=sys.stderr)
        return 1
    print(f"check_embedded_markup: 0 embedded documents over {len(os.listdir(ROOT))} "
          f"path(s) ({len(WAIVERS)} waived)")
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

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        # ⚑ THE SCAN MUST SEE A PLANTED ARTIFACT, or its all-clear means nothing.
        open(os.path.join(td, "emb.py"), "w").write(
            'X = """<svg>\n' + "\n".join(f"  <rect id='{i}'/>" for i in range(12))
            + '\n</svg>"""\n')
        check("sees a planted SVG document", len(findings(td)) , 1)
        # ⚑ A DOCSTRING MENTIONING MARKUP IS PROSE, NOT AN ARTIFACT. This file's
        # own docstring says `<svg`; if that fired, the tool would refuse itself.
        open(os.path.join(td, "doc.py"), "w").write(
            '"""A long docstring about <svg documents.\n' + "\n" * 12 + '"""\nY = 1\n')
        planted = [f for f in findings(td) if f[0] == "doc.py"]
        check("a docstring about markup does not fire", planted, [])
        # ⚑ A SMALL PRIMITIVE IS NOT A DOCUMENT.
        open(os.path.join(td, "prim.py"), "w").write('Z = "<svg><rect/></svg>"\n')
        check("a one-line primitive does not fire",
              [f for f in findings(td) if f[0] == "prim.py"], [])
    check("this tool does not fire on itself",
          [f for f in findings() if f[0] == "check_embedded_markup.py"], [])

    # ⚑ IDENTIFICATION ALONE WOULD FIRE ON PROSE, AND POSITION IS WHAT SAVES IT.
    # A docstring DESCRIBING QML identifies AS QML — measured in identify.py's
    # own selftest. So the docstring guard above is not belt-and-braces: without
    # it this tool reports its own documentation as an embedded artifact. Assert
    # the hazard is real, so nobody later "simplifies" the guard away.
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    try:
        import identify
        prose = ("The QML lives in templates/, not here. A generator that "
                 "writes\n\n    import QtQuick\n    Item { id: root }\n\n"
                 "inline has hidden an artifact inside a program.\n")
        check("prose about QML DOES identify as QML (position is the guard)",
              identify.of_string(prose), "text/x-qml")
    except ImportError:
        check("identify.py is importable", False, True)
    check("every waiver carries a reason", all(WAIVERS.values()), True)
    print("check_embedded_markup selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
