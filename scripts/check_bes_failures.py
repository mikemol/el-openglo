#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""bes_failures.py — what FAILED in a BuildBuddy invocation, from its id (W759, under W754)

A refused gate prints a BuildBuddy URL and a truncated tail. The full record is a 97K-token JSON
document (the whole Build Event Protocol stream), so a reader asking "which claim was undischarged"
either spends the context or guesses. This asks the record instead:

    scripts/check_bes_failures.py INVOCATION_ID      # failed targets, then the progress lines that name a failure
    scripts/check_bes_failures.py --file inv.json    # the same over a saved GetInvocation response
    scripts/check_bes_failures.py --shape inv.json   # the record's key paths with counts
    scripts/check_bes_failures.py --selftest

It prints `n of m`: failed test targets of the test targets the record holds. A record with no test
target at all is REFUSED (exit 2), not read as a clean build: the id or the shape is wrong.

WEAKNESS, STATED. The BES JSON is walked generically (any object with an `overallStatus` beside a
`label`-bearing id, any string under `stdout`/`stderr`), because the exact nesting is the service's
and was not documented here; a shape it changes silently yields fewer lines, and the `n of m` line
says how many targets it saw. The fetch needs the in-cluster service name, which resolves from this
shell (127.0.0.1:31080 does not).
"""

import json
import sys
import urllib.request

RPC = "http://buildbuddy-web.buildbuddy.svc.cluster.local:8080/rpc/BuildBuddyService/GetInvocation"
FAILURE_WORDS = ("FAIL", "undischarged", "REFUSED", "Error", "error:")
TAIL = 40
Path = tuple[str, ...]


def fetch(invocation_id: str) -> dict[str, object]:
    body = json.dumps({"lookup": {"invocation_id": invocation_id}}).encode()
    req = urllib.request.Request(
        RPC, data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        doc: dict[str, object] = json.loads(resp.read())
    return doc


def walk(node: object, path: Path = ()) -> list[tuple[Path, object]]:
    """Every (key path, value) of a JSON document, depth first."""
    out: list[tuple[Path, object]] = []
    if isinstance(node, dict):
        for k, v in node.items():
            out.append(((*path, k), v))
            out.extend(walk(v, (*path, k)))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out.append(((*path, str(i)), v))
            out.extend(walk(v, (*path, str(i))))
    return out


def targets(doc: object) -> dict[str, str]:
    """{label: overallStatus} of every test target the record holds (targetGroups[].targets[])."""
    out: dict[str, str] = {}
    for _path, v in walk(doc):
        if not isinstance(v, dict):
            continue
        meta, summary = v.get("metadata"), v.get("testSummary")
        if not (isinstance(meta, dict) and isinstance(summary, dict)):
            continue
        label, status = meta.get("label"), summary.get("overallStatus")
        if isinstance(label, str) and isinstance(status, str):
            out[label] = status
    return out


def failed_logs(doc: object) -> dict[str, list[str]]:
    """{label: [uri]} of the test logs the record lists as failed (the log body is in the remote cache)."""
    out: dict[str, list[str]] = {}
    for _path, v in walk(doc):
        if not isinstance(v, dict):
            continue
        meta, summary = v.get("metadata"), v.get("testSummary")
        if not (isinstance(meta, dict) and isinstance(summary, dict)):
            continue
        label, failed = meta.get("label"), summary.get("failed")
        if isinstance(label, str) and isinstance(failed, list):
            out[label] = [
                f["uri"] for f in failed if isinstance(f, dict) and "uri" in f
            ]
    return out


def progress_lines(doc: object) -> list[str]:
    """The stdout/stderr lines of the progress events that name a failure, in order."""
    lines: list[str] = []
    for path, v in walk(doc):
        if path and path[-1] in ("stdout", "stderr") and isinstance(v, str):
            lines.extend(
                ln for ln in v.splitlines() if any(w in ln for w in FAILURE_WORDS)
            )
    return lines


def shape(doc: object) -> list[str]:
    """The distinct key paths of a record with array positions elided, each with its count."""
    counts: dict[str, int] = {}
    for path, _v in walk(doc):
        key = ".".join("[]" if p.isdigit() else p for p in path)
        counts[key] = counts.get(key, 0) + 1
    return [f"{n}\t{k}" for k, n in sorted(counts.items())]


def report(doc: object) -> tuple[list[str], int]:
    """(output lines, exit code): 2 when the record holds no test target."""
    seen = targets(doc)
    if not seen:
        return ["bes_failures: the record holds no test target; wrong id or shape"], 2
    failed = sorted(label for label, st in seen.items() if st != "PASSED")
    logs = failed_logs(doc)
    out = [f"FAILED {label} {seen[label]}" for label in failed]
    out.extend(f"  log {uri}" for label in failed for uri in logs.get(label, []))
    out.extend(progress_lines(doc)[-TAIL:])
    out.append(f"bes_failures: {len(failed)} of {len(seen)} test target(s) not PASSED")
    return out, 0


def _selftest() -> bool:
    ok = True

    def chk(label: str, got: object, want: object) -> None:
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    doc = {
        "invocation": [
            {
                "targetGroups": [
                    {
                        "targets": [
                            {
                                "metadata": {"label": "//:worklist"},
                                "testSummary": {
                                    "overallStatus": "FAILED",
                                    "failed": [{"uri": "bytestream://x/test.log"}],
                                },
                            },
                            {
                                "metadata": {"label": "//:ok"},
                                "testSummary": {"overallStatus": "PASSED"},
                            },
                        ]
                    }
                ],
                "event": [
                    {"buildEvent": {"progress": {"stderr": "REFUSED X (undischarged)"}}}
                ],
            }
        ]
    }
    lines, rc = report(doc)
    chk(
        "a failed target is named beside the n of m",
        (rc, lines[-1]),
        (0, "bes_failures: 1 of 2 test target(s) not PASSED"),
    )
    chk("the target is named", "FAILED //:worklist FAILED" in lines, True)
    chk("its failed log is listed", "  log bytestream://x/test.log" in lines, True)
    chk(
        "the failing progress line is carried",
        "REFUSED X (undischarged)" in lines,
        True,
    )
    chk(
        "a passing target is not listed as failed",
        any("//:ok" in ln for ln in lines),
        False,
    )
    chk("a record with no test target is refused, not clean", report({"a": 1})[1], 2)
    print("bes_failures selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv: list[str]) -> int:
    args = argv[1:]
    if args == ["--selftest"]:
        return 0 if _selftest() else 1
    if len(args) == 2 and args[0] == "--shape":
        with open(args[1], encoding="utf-8") as fh:
            print("\n".join(shape(json.load(fh))))
        return 0
    if len(args) == 2 and args[0] == "--file":
        with open(args[1], encoding="utf-8") as fh:
            doc: object = json.load(fh)
    elif len(args) == 1 and not args[0].startswith("--"):
        doc = fetch(args[0])
    else:
        print(f"bes_failures: unknown arguments {args!r}", file=sys.stderr)
        return 2
    lines, rc = report(doc)
    print("\n".join(lines))
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv))
