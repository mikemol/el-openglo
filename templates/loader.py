#!/usr/bin/env python3
"""templates/loader.py — read an artifact from a file, substitute, return it.

⚑ WHY TEMPLATES ARE FILES.  A generator that builds SVG or QML by concatenating
string literals has hidden an ARTIFACT inside a PROGRAM. Nobody can open it, no
viewer renders it, no schema validator or qmllint reaches it, and a diff shows
"the .py changed" rather than which element moved. The wallpaper was the extreme
case — its whole SVG was built at module level and written as an import side
effect, so the only way to SEE it was to run the module.

    render("SegmentChar.qml")                  # a constant artifact
    render("live-wallpaper.qml", lit="#99ffeb")  # one with holes

⚑ SUBSTITUTION IS `$name`, NOT `{name}`, AND THE REASON IS QML.  QML and CSS are
brace languages: `Item { id: root }`. Under str.format or an f-string every one
of those braces must be doubled, which is why the embedded versions in this tree
are littered with `{{` and `}}`. string.Template uses `$name`, so a template file
is the artifact VERBATIM — it opens in a QML editor, lints, and previews, because
nothing was escaped to survive being a Python literal.

⚑ A MISSING HOLE IS AN ERROR, NEVER A BLANK.  `substitute` (not `safe_substitute`)
raises on an unfilled `$name`. A silently-blank colour renders as black and looks
like a design decision; the whole point of moving these out of the source is that
failures become visible rather than plausible.
"""
import os
import string
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def path_for(name, root=None):
    """Absolute path of a template, without reading it."""
    return os.path.join(root or HERE, name)


def read(name, root=None):
    """The template's raw text — no substitution, for previewing or linting."""
    with open(path_for(name, root), encoding="utf-8") as fh:
        return fh.read()


def render(name, root=None, **holes):
    """The template with `$name` holes filled. Raises on an unfilled hole.

    A template with NO holes is the common case here (SegmentChar, the kcfg
    documents): it round-trips unchanged, which is what makes it previewable."""
    text = read(name, root)
    if not holes:
        # ⚑ NO HOLES MEANS NO SUBSTITUTION PASS.  Running Template over a
        # hole-less artifact would still choke on a literal `$` in its content —
        # a QML binding or a CSS variable — so a constant artifact is returned
        # verbatim rather than parsed for holes it does not have.
        return text
    return string.Template(text).substitute(**holes)


def names(root=None):
    """Every template this directory holds, sorted."""
    d = root or HERE
    return sorted(f for f in os.listdir(d)
                  if not f.startswith((".", "_")) and not f.endswith(".py"))


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
        open(os.path.join(td, "plain.qml"), "w").write("Item { id: root }\n")
        open(os.path.join(td, "holed.qml"), "w").write("color: $lit\nItem { }\n")
        # ⚑ BRACES SURVIVE UNTOUCHED — the property this exists for.
        check("a brace artifact round-trips", render("plain.qml", root=td),
              "Item { id: root }\n")
        check("a hole is filled", render("holed.qml", root=td, lit="#99ffeb"),
              "color: #99ffeb\nItem { }\n")
        # ⚑ AN UNFILLED HOLE RAISES rather than rendering blank.
        try:
            render("holed.qml", root=td, wrong="x")
            check("an unfilled hole raises", "returned", "raised")
        except (KeyError, ValueError):
            check("an unfilled hole raises", "raised", "raised")
        check("names() lists templates", names(td), ["holed.qml", "plain.qml"])
    print("loader selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    for n in names():
        print(n)
