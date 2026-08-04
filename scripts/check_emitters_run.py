#!/usr/bin/env python3
"""check_emitters_run.py — the generators actually RUN, not merely compile.

⚑ THE WITNESS THAT WOULD HAVE CAUGHT THE PARTIAL FILES.  check_compiles.py passes
every one of these, and said so in its own docstring: compiling proves the syntax
survived the recovery and nothing more.  Three real defects hid behind it, all in
files the archive marked ** PARTIAL **, none of them a syntax error:

  · make_schemes.py  — a module-level forward reference (a duplicated solver-flag
    block placed BEFORE the table it reads), plus a mangled identifier
    `_AUTHORED__AUTHORED_GRID` from a mis-anchored replay edit.  NameError at import.
  · make_konsole.py  — called `reference_floors()` (plural, dict-shaped); cvd_gate
    defines `reference_floor()` returning a tuple.  AttributeError at run.
  · make_chrome.py   — its __main__ named six variants before the schemes that
    define them had been emitted.

A generator's whole job is to WRITE something.  So the check runs it, in dependency
order, and asks for exit 0.

    scripts/check_emitters_run.py          # exit 0 iff each runs
    scripts/check_emitters_run.py --list   # the order they run in, and why

⚑ ORDER IS A FACT ABOUT THE PIPELINE, NOT A PREFERENCE.  make_schemes writes the
`.colors` files every token-reading emitter then parses, so it goes first; running
them alphabetically reports a missing INPUT as a broken EMITTER.

⚑ AN EMITTER WHOSE EXTERNAL INPUT IS ABSENT IS A SKIP, COUNTED AND NAMED — a fact
about this machine, not about the theme.  make_kvantum recolours the upstream
KvFlat theme; without it staged there is nothing to recolour.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (module, why it sits here) — dependency order, not alphabetical.
ORDER = (
    ("make_schemes",   "writes the .colors files every other emitter reads"),
    ("make_preview",   "owns parse_scheme; renders the previews"),
    ("make_chrome",    "browser manifests, from the scheme tokens"),
    ("make_konsole",   "terminal scheme, from the scheme tokens"),
    ("make_aurorae",   "window decoration, from GRID"),
    ("make_plasma",    "Plasma theme SVGs, from GRID"),
    ("make_wallpaper", "wallpaper; sources tokens with a standalone fallback"),
)

# Emitters that need an input this machine may not have.  Absent -> SKIP, named.
EXTERNAL = {
    "make_kvantum": ("/tmp/KvFlat.kvconfig",
                     "recolours the upstream KvFlat theme; stage it to run this"),
}


def main(argv):
    known = {"--list"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_emitters_run: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--list" in argv:
        for i, (m, why) in enumerate(ORDER, 1):
            print(f"{i}. {m}\t{why}")
        for m, (need, why) in EXTERNAL.items():
            print(f"-  {m}\tneeds {need} — {why}")
        return 0

    ok, failed, skipped = [], [], []
    for mod, _why in ORDER:
        p = os.path.join(ROOT, mod + ".py")
        if not os.path.exists(p):
            failed.append((mod, "module file absent"))
            continue
        r = subprocess.run([sys.executable, p], cwd=ROOT,
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            tail = (r.stderr or r.stdout).strip().splitlines()
            failed.append((mod, tail[-1] if tail else f"exit {r.returncode}"))
        else:
            ok.append(mod)
    for mod, (need, why) in EXTERNAL.items():
        if os.path.exists(need):
            p = os.path.join(ROOT, mod + ".py")
            r = subprocess.run([sys.executable, p], cwd=ROOT,
                               capture_output=True, text=True, timeout=600)
            (ok if r.returncode == 0 else failed).append(
                mod if r.returncode == 0 else (mod, "ran but failed"))
        else:
            skipped.append((mod, why))

    total = len(ORDER) + len(EXTERNAL)
    if failed:
        print(f"check_emitters_run: REFUSED — {len(failed)} of {total} did not run:",
              file=sys.stderr)
        for mod, why in failed:
            print(f"    {mod}: {why}", file=sys.stderr)
        return 1
    note = "".join(f"\n    SKIP {m} — {why}" for m, why in skipped)
    print(f"check_emitters_run: {len(ok)} ran, {len(skipped)} skipped of {total}{note}")
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

    check("order is non-empty", len(ORDER) > 0, True)
    check("make_schemes runs first (it writes the inputs)", ORDER[0][0], "make_schemes")
    stale = [m for m, _ in ORDER if not os.path.exists(os.path.join(ROOT, m + ".py"))]
    check(f"no module in the order is missing ({stale})", stale, [])
    check("every external need is explained", all(w for _, w in EXTERNAL.values()), True)
    print("check_emitters_run selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
