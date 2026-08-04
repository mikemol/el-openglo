#!/usr/bin/env python3
"""extract_template.py — move an embedded artifact out of source, verbatim.

⚑ THE EXTRACTION MUST BE BYTE-EXACT, WHICH IS WHY IT IS A TOOL.  Copy-pasting an
87-line QML component out of a Python literal by hand invites exactly one class
of error — a lost trailing newline, a de-escaped brace, an unnoticed `\\n` — and
the result still LOOKS right, because QML tolerates most of it. Reading the value
from the module and writing those bytes cannot drift.

    scripts/extract_template.py <module> <accessor> <template-name>
    scripts/extract_template.py --verify <module> <accessor> <template-name>

`--verify` re-reads both and reports whether they still agree, which is the mode
that matters after the source is rewritten to READ the template: it proves the
rewrite did not change the artifact.
"""
import importlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(ROOT, "templates")


def value_of(module, accessor):
    """The artifact a module holds, whether a constant or a zero-arg function."""
    sys.path.insert(0, ROOT)
    mod = importlib.import_module(module)
    obj = getattr(mod, accessor)
    return obj() if callable(obj) else obj


def main(argv):
    verify = "--verify" in argv
    args = [a for a in argv[1:] if not a.startswith("--")]
    for a in argv[1:]:
        if a.startswith("--") and a != "--verify":
            print(f"extract_template: unknown flag {a!r}", file=sys.stderr)
            return 2
    if len(args) != 3:
        print("usage: extract_template.py [--verify] <module> <accessor> <name>",
              file=sys.stderr)
        return 2
    module, accessor, name = args
    try:
        text = value_of(module, accessor)
    except Exception as e:                       # noqa: BLE001
        print(f"extract_template: REFUSED — cannot read {module}.{accessor}: "
              f"{type(e).__name__}: {e}", file=sys.stderr)
        return 2
    if not isinstance(text, str):
        print(f"extract_template: REFUSED — {module}.{accessor} is "
              f"{type(text).__name__}, not a string", file=sys.stderr)
        return 2

    path = os.path.join(TEMPLATES, name)
    if verify:
        if not os.path.isfile(path):
            print(f"extract_template: REFUSED — no template at {name}", file=sys.stderr)
            return 1
        on_disk = open(path, encoding="utf-8").read()
        if on_disk != text:
            print(f"extract_template: DIFFERS — {module}.{accessor} and {name} "
                  f"no longer agree ({len(text)} vs {len(on_disk)} bytes)",
                  file=sys.stderr)
            return 1
        print(f"extract_template: {name} matches {module}.{accessor} "
              f"({len(text)} bytes)")
        return 0

    os.makedirs(TEMPLATES, exist_ok=True)
    open(path, "w", encoding="utf-8").write(text)
    print(f"extract_template: wrote {name} ({len(text)} bytes) "
          f"from {module}.{accessor}")
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

    check("a callable accessor is called",
          value_of("templates.loader", "names").__class__ is list, True)
    check("templates dir is under the repo", TEMPLATES.startswith(ROOT), True)
    print("extract_template selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
