#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_log_content.py — no shipped QML/JS log call carries notification content.

⚑ WHY (luthen-observability, 2026-10-01). The marquee's trace() printed the ticker
text — senders, subjects and message bodies — to plasmashell's stderr, which lands
in the user journal, which luthen ships to VictoriaLogs: personal content in a store
agents read routinely (~200 lines a day; earliest 2026-09-29). The same trace also
persisted into plasmoid.configuration.traceLog, i.e. the appletsrc on disk.

So this MEASURES every log call in the shipped templates — console.log/info/warn/
debug/error, print(, and any `trace(` — with its argument expression (read by
balanced parentheses, strings skipped) and the identifiers in it that carry
CONTENT. policy/log_content.rego decides.

    scripts/check_log_content.py --json      # the measurement
    scripts/check_log_content.py --list      # every call, flagged
    scripts/check_log_content.py --selftest

WEAKNESS, STATED. Content is recognised by NAME (CONTENT_NAMES), not by data flow:
a content value copied into a new variable with an innocent name and then logged is
invisible. The names are the marquee's own content carriers; a new carrier must be
added here. Only the templates/ population is read — the emitted packages are
generated from it — and Python build tools are out of scope (they print build data,
not user content). A `.length` read of a content name is structure, and is allowed.
"""

import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# names that hold notification content in the marquee (text, summary, body, links, labels)
CONTENT_NAMES = frozenset(
    {
        "tickerText",
        "text",
        "summary",
        "sum",
        "body",
        "link",
        "href",
        "label",
        "labels",
        "paintedText",
        "idleText",
        "did",
        "joined",
        "item",
        "run",
    }
)
CALL_RE = re.compile(r"\b(console\.(?:log|info|warn|debug|error)|print|trace)\s*\(")
IDENT_RE = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*(?:\s*\.\s*[A-Za-z_$][A-Za-z0-9_$]*)*")


def _argument(src, i):
    """The text between the '(' at src[i] and its matching ')', skipping string literals."""
    depth, j, quote = 0, i, None
    while j < len(src):
        c = src[j]
        if quote:
            if c == "\\":
                j += 2
                continue
            if c == quote:
                quote = None
        elif c in "\"'`":
            quote = c
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return src[i + 1 : j]
        j += 1
    return src[i + 1 :]


def _strip_strings(s):
    return re.sub(r"\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`", '""', s)


def content_names(arg):
    """Content names referenced in an argument, except as a `.length` read."""
    found = set()
    for m in IDENT_RE.finditer(_strip_strings(arg)):
        parts = [p.strip() for p in m.group(0).split(".")]
        if parts and parts[-1] == "length":
            continue
        for p in parts:
            if p in CONTENT_NAMES:
                found.add(p)
    return sorted(found)


def calls(src, rel):
    out = []
    for m in CALL_RE.finditer(src):
        if m.group(1) == "trace" and src[
            max(0, m.start() - 9) : m.start()
        ].rstrip().endswith("function"):
            continue  # the definition, not a call
        arg = _argument(src, m.end() - 1)
        line = src.count("\n", 0, m.start()) + 1
        out.append(
            {"id": f"{rel}:{line}", "call": m.group(1), "content": content_names(arg)}
        )
    return out


def measure(root=ROOT):
    files = sorted(
        glob.glob(os.path.join(root, "templates", "*.qml"))
        + glob.glob(os.path.join(root, "templates", "*.js"))
    )
    cases = []
    for p in files:
        with open(p, encoding="utf-8") as fh:
            text = fh.read()
        cases += calls(text, os.path.relpath(p, root))
    return {"files": len(files), "cases": cases}


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            ("  ok   " if got == want else "  FAIL ")
            + label
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    leak = 'root.trace("rebuild count=" + n + " ticker=" + JSON.stringify(root.tickerText));'
    safe = 'root.trace("rebuild count=" + n + " tickerLen=" + root.tickerText.length);'
    chk(
        "a traced ticker text is SEEN",
        calls(leak, "x.qml")[0]["content"],
        ["tickerText"],
    )
    chk("...and its length alone is structure", calls(safe, "x.qml")[0]["content"], [])
    chk(
        "a content word inside a string literal is not a reference",
        calls('console.log("text=" + count)', "x.js")[0]["content"],
        [],
    )
    chk(
        "a link href is SEEN",
        calls('trace("tap " + JSON.stringify(did))', "x.qml")[0]["content"],
        ["did"],
    )
    chk(
        "the trace definition is not counted as a call",
        calls('function trace(what) { console.log("el " + what); }', "x.qml")[0][
            "call"
        ],
        "console.log",
    )
    real = measure()
    chk(
        "the real templates are read",
        real["files"] > 0 and len(real["cases"]) > 0,
        True,
    )
    print("check_log_content selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    for a in argv[1:]:
        if a not in ("--json", "--list", "--selftest"):
            print(f"check_log_content: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    m = measure()
    if "--json" in argv:
        print(json.dumps(m, indent=1))
        return 0
    if "--list" in argv:
        for c in m["cases"]:
            print(
                f"  {c['id']:40} {c['call']:12} {'CONTENT ' + str(c['content']) if c['content'] else 'ok'}"
            )
        bad = sum(1 for c in m["cases"] if c["content"])
        print(
            f"check_log_content: {len(m['cases']) - bad} of {len(m['cases'])} log call(s) carry no content "
            f"over {m['files']} template file(s)"
        )
        return 0
    print("usage: check_log_content.py --json | --list | --selftest", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
