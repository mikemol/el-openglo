#!/usr/bin/env python3
"""drop_lines.py — delete an inclusive line range from a file, by number.

⚑ WHY A TOOL FOR SOMETHING SO SMALL.  Removing an 87-line block by hand means
reproducing its first and last lines exactly in an edit anchor — and those lines
are markup, full of the braces and escapes that make transcription unreliable.
The line numbers are already known (a scanner reported them); acting on the
numbers cannot mis-transcribe.

    scripts/drop_lines.py <file> <first> <last>          # delete, inclusive
    scripts/drop_lines.py --show <file> <first> <last>   # print what would go

⚑ IT REFUSES A RANGE THAT DOES NOT PARSE AFTERWARD.  Deleting a block from
Python that leaves a syntax error is worse than leaving the block: the file
stops compiling and the reason is a range nobody re-checked. The result is
parsed before it is written, and the write is abandoned if it does not.
"""
import ast
import os
import sys


def main(argv):
    show = "--show" in argv
    args = [a for a in argv[1:] if not a.startswith("--")]
    for a in argv[1:]:
        if a.startswith("--") and a != "--show":
            print(f"drop_lines: unknown flag {a!r}", file=sys.stderr)
            return 2
    if len(args) != 3:
        print("usage: drop_lines.py [--show] <file> <first> <last>", file=sys.stderr)
        return 2
    path, first, last = args[0], int(args[1]), int(args[2])
    if not os.path.isfile(path):
        print(f"drop_lines: REFUSED — no such file {path}", file=sys.stderr)
        return 2
    lines = open(path, encoding="utf-8").read().splitlines(keepends=True)
    if not (1 <= first <= last <= len(lines)):
        print(f"drop_lines: REFUSED — range {first}..{last} is outside "
              f"1..{len(lines)}", file=sys.stderr)
        return 2

    if show:
        sys.stdout.write("".join(lines[first - 1:last]))
        return 0

    kept = lines[:first - 1] + lines[last:]
    text = "".join(kept)
    if path.endswith(".py"):
        try:
            ast.parse(text)
        except SyntaxError as e:
            print(f"drop_lines: REFUSED — the result would not parse: {e}",
                  file=sys.stderr)
            return 1
    open(path, "w", encoding="utf-8").write(text)
    print(f"drop_lines: removed {last - first + 1} line(s) from {path} "
          f"({len(lines)} -> {len(kept)})")
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
        p = os.path.join(td, "a.py")
        open(p, "w").write("A = 1\nB = 2\nC = 3\nD = 4\n")
        check("drops the named range", main(["drop_lines", p, "2", "3"]), 0)
        check("kept the rest", open(p).read(), "A = 1\nD = 4\n")
        # ⚑ A DELETION THAT BREAKS THE PARSE IS REFUSED, NOT WRITTEN.
        p2 = os.path.join(td, "b.py")
        open(p2, "w").write("def f():\n    return 1\n")
        check("refuses a range that breaks the parse",
              main(["drop_lines", p2, "2", "2"]), 1)
        check("left the file untouched", open(p2).read(), "def f():\n    return 1\n")
        check("refuses an out-of-range span", main(["drop_lines", p, "1", "99"]), 2)
    print("drop_lines selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
