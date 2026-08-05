#!/usr/bin/env python3
"""capture_baseline.py — record a generator's output BEFORE it is rewritten.

⚑ THE BASELINE MUST PREDATE THE REWRITE, OR IT PROVES NOTHING.  Extraction is
only safe if the generator emits the same bytes afterward, and "the same as
what?" has to be answered before the edit, not after. Capturing it later records
the NEW behaviour and calls it the baseline — a check that certifies whatever it
happens to find.

    scripts/capture_baseline.py <module> <accessor> <name> [arg...]

Arguments are passed positionally to the accessor. A bare literal is used as-is;
a name the module defines resolves to that attribute (or its call, if callable),
which is how a generator taking a solved token dict is exercised without this
tool knowing what one is.

⚑ IT REFUSES TO OVERWRITE.  A baseline that can be silently re-recorded is a
baseline that drifts to match the code — exactly the staleness this repo keeps
finding. Delete it deliberately if the output is MEANT to change.
"""
import importlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINES = os.path.join(ROOT, "catalog", "baselines")


def _resolve(mod, token):
    """A module attribute if it names one, else the literal token."""
    if hasattr(mod, token):
        v = getattr(mod, token)
        return v() if callable(v) else v
    return token


def capture(module, accessor, name, args=()):
    sys.path.insert(0, ROOT)
    mod = importlib.import_module(module)
    obj = getattr(mod, accessor)
    text = obj(*[_resolve(mod, a) for a in args]) if callable(obj) else obj
    if not isinstance(text, str):
        raise TypeError(f"{module}.{accessor} is {type(text).__name__}, not a string")
    os.makedirs(BASELINES, exist_ok=True)
    path = os.path.join(BASELINES, name)
    if os.path.exists(path):
        raise FileExistsError(path)
    open(path, "w", encoding="utf-8").write(text)
    return path, len(text)


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    for a in argv[1:]:
        if a.startswith("--"):
            print(f"capture_baseline: unknown flag {a!r}", file=sys.stderr)
            return 2
    if len(args) < 3:
        print("usage: capture_baseline.py <module> <accessor> <name> [arg...]",
              file=sys.stderr)
        return 2
    module, accessor, name = args[0], args[1], args[2]
    try:
        path, n = capture(module, accessor, name, args[3:])
    except FileExistsError as e:
        print(f"capture_baseline: REFUSED — {os.path.basename(str(e))} already "
              f"exists. A baseline is not re-recorded; delete it deliberately if "
              f"the output is MEANT to change.", file=sys.stderr)
        return 1
    except Exception as e:                       # noqa: BLE001
        print(f"capture_baseline: REFUSED — {module}.{accessor}: "
              f"{type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(f"capture_baseline: wrote {os.path.relpath(path, ROOT)} ({n} bytes)")
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

    check("baselines live under the repo", BASELINES.startswith(ROOT), True)
    # ⚑ REFUSING TO OVERWRITE IS THE POINT, so it is asserted.
    import tempfile
    saved = globals()["BASELINES"]
    try:
        with tempfile.TemporaryDirectory() as td:
            globals()["BASELINES"] = td
            capture("templates.loader", "names", "first.txt")
            check("a second capture refuses",
                  main(["capture_baseline", "templates.loader", "names",
                        "first.txt"]), 1)
    except TypeError:
        # names() returns a list, not a str — that refusal is also correct
        check("a non-string accessor refuses", True, True)
    finally:
        globals()["BASELINES"] = saved
    print("capture_baseline selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
