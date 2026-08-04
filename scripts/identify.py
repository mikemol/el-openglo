#!/usr/bin/env python3
"""identify.py — what KIND of content is this? For files and for strings alike.

⚑ WHY THIS OWNS THE QUESTION.  check_embedded_markup.py carried a hand-written
`MARKUP` tuple — `("<svg", "<?xml", "import QtQuick", …)` — which is a worse
libmagic that I maintain. libmagic already knows how to identify content, and
where it does not, its database is EXTENSIBLE. A guessed tuple in one checker is
the reasoning-not-codified shape: the next reader adds a kind and forgets the
tuple.

    scripts/identify.py <path>...        # identify files
    scripts/identify.py --string <text>  # identify content with no filename
    scripts/identify.py --db             # which magic databases are in play
    scripts/identify.py --kinds          # every kind this repo has signatures for

⚑ A STRING AND A FILE ARE THE SAME QUESTION, which is the point. A Python string
literal and a markdown fenced code block are both TYPED CONTAINERS whose payload
is another language; identifying the payload is what lets an extractor move it to
a file the container then reads. That is worth doing on its own — the container
becomes compilable or dynamically loadable — regardless of whether anything ever
parses the payload.

⚑ THE REPO DATABASE AUGMENTS, IT DOES NOT REPLACE.  Stock file(1) returns
text/plain for QML, .colors and .bib. Pointing libmagic at the repo file ALONE
fixes those and breaks SVG and Python, which the system database was handling.
Both are loaded, repo first.

⚑ IDENTIFICATION IS NOT PARSING, AND THE DIFFERENCE IS LOAD-BEARING.  This says
"that looks like QML"; it does not say the QML is well-formed, and no caller may
read it as though it did. A docstring DESCRIBING QML identifies as QML — measured
— so a caller that dispatches on kind alone will hand its own prose to a QML
handler. Position and parse are the caller's guards; kind is only the first.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_DB = os.path.join(ROOT, "magic", "el-openglo.magic")

# Where the system database may live. The first that exists wins.
SYSTEM_DB = ("/usr/share/misc/magic.mgc", "/usr/share/file/magic.mgc",
             "/etc/magic")


def system_db():
    """The system magic database in play, or None if none is found."""
    return next((p for p in SYSTEM_DB if os.path.exists(p)), None)


def magic_path():
    """The colon-joined database list: repo signatures FIRST, then the system.

    ⚑ ORDER AND PRESENCE BOTH MATTER.  Repo-first so a local signature can win a
    tie; system-included so the kinds libmagic already knows keep working."""
    parts = [p for p in (REPO_DB, system_db()) if p and os.path.exists(p)]
    return ":".join(parts)


def _magic(mime=True):
    import magic
    return magic.Magic(mime=mime, magic_file=magic_path() or None)


def of_bytes(data, mime=True):
    """The kind of a byte string — the mode a string literal needs."""
    try:
        return _magic(mime).from_buffer(data)
    except Exception as e:                       # noqa: BLE001
        return f"(unidentifiable: {type(e).__name__})"


def of_string(text, mime=True):
    return of_bytes(text.encode("utf-8", "replace"), mime)


def of_file(path, mime=True):
    try:
        return _magic(mime).from_file(path)
    except Exception as e:                       # noqa: BLE001
        return f"(unidentifiable: {type(e).__name__})"


def kinds():
    """[(mime, description)] this repo declares signatures for."""
    out = []
    if not os.path.exists(REPO_DB):
        return out
    desc = None
    for line in open(REPO_DB, encoding="utf-8"):
        s = line.strip()
        if s.startswith("!:mime"):
            out.append((s.split(None, 1)[1].strip(), desc or ""))
        elif s and not s.startswith("#"):
            parts = s.split("\t")
            desc = parts[-1].strip() if len(parts) > 1 else s
    return out


def main(argv):
    known = {"--string", "--db", "--kinds", "--describe"}
    flags = [a for a in argv[1:] if a.startswith("--")]
    args = [a for a in argv[1:] if not a.startswith("--")]
    for f in flags:
        if f not in known:
            print(f"identify: unknown flag {f!r}", file=sys.stderr)
            return 2
    mime = "--describe" not in flags

    if "--db" in flags:
        print(f"repo:   {REPO_DB}{'' if os.path.exists(REPO_DB) else '  (ABSENT)'}")
        print(f"system: {system_db() or '(none found)'}")
        print(f"in use: {magic_path() or '(none)'}")
        return 0
    if "--kinds" in flags:
        for m, d in kinds():
            print(f"{m}\t{d}")
        return 0
    if "--string" in flags:
        if not args:
            print("identify: --string needs the text", file=sys.stderr)
            return 2
        print(of_string(" ".join(args), mime))
        return 0
    if not args:
        print("usage: identify.py <path>... | --string <text> | --db | --kinds",
              file=sys.stderr)
        return 2
    missing = [p for p in args if not os.path.exists(p)]
    if missing:
        print(f"identify: REFUSED — no such path(s): {missing}", file=sys.stderr)
        return 2
    width = max(len(p) for p in args)
    for p in args:
        print(f"{p:<{width}}  {of_file(p, mime)}")
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

    check("a system database is found", system_db() is not None, True)
    check("the repo database exists", os.path.exists(REPO_DB), True)
    # ⚑ BOTH DATABASES, OR THE REPO ONE SILENTLY BREAKS THE STOCK KINDS.
    check("both databases are in play", magic_path().count(":"), 1)
    check("the repo db is first", magic_path().startswith(REPO_DB), True)

    # the four kinds this repo added signatures for
    check("QML identifies", of_string("// c\nimport QtQuick\nItem { }\n"),
          "text/x-qml")
    check("a colour scheme identifies",
          of_string("[ColorEffects:Disabled]\nColor=6,11,13\n"),
          "text/x-kde-colorscheme")
    check("warrants identify",
          of_string("% a header\n" * 4 + "@misc{KEY,\n  claim = {x}\n}\n"),
          "text/x-bibtex")
    # ⚑ AND THE STOCK KINDS STILL WORK — the regression the repo-only db caused.
    check("SVG still identifies",
          of_string('<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>'),
          "image/svg+xml")
    check("Python still identifies",
          of_string("#!/usr/bin/env python3\nimport os\n\n\ndef f():\n    return 1\n"),
          "text/x-script.python")

    # ⚑ IDENTIFICATION IS NOT PARSING, and this is the measured proof: prose
    # DESCRIBING QML identifies AS QML. A caller dispatching on kind alone will
    # hand its own documentation to a QML handler.
    prose = ("    The QML lives in templates/SegmentChar.qml, not here. A "
             "generator that writes\n\n        import QtQuick\n        "
             "Item { id: root }\n\n    inline has hidden an artifact.\n")
    check("prose about QML identifies as QML (the caller must guard)",
          of_string(prose), "text/x-qml")

    check("every declared kind has a mime", all(m for m, _ in kinds()), True)
    check("kinds() finds the four signatures", len(kinds()), 4)
    print("identify selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
