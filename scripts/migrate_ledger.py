#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""migrate_ledger.py — how much of the ledger can a structured reader read? (W89, under W91)

The ledger is `.claude/paths-forward.ledger`; mtools' own reader (mikemol.pathsforward.ledger.parse) reads a
line as `stamp kind symbol outcome mechanism "note" [evidence=...]` and returns the rest as Unparsed, with a
`why`. The legacy lines (hand echoes, `state_hash=` in place of `evidence=`, free text) are kept whole there
and nemik cannot read them. This is the first step: MEASURE them.

    scripts/migrate_ledger.py --report      # n of m lines parse; the unparsed, by reason and by legacy shape
    scripts/migrate_ledger.py --selftest

⚑ WEAKNESS, STATED. --report only reads: it rewrites nothing, and the legacy SHAPE it names is a first-token
heuristic (a stamp, a bare symbol, free text), not a grammar. The rewrite (--write, with the kind taken from
the line's origin, the symbol extracted and the full text kept as the note) is the next step and is not here.
"""

import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, ".claude", "paths-forward.ledger")
OFFSET_STAMP = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00$")
QUOTED = re.compile(r"'[^']*'")


def shape(raw):
    """The legacy shape of an unparsed line: what its first token looks like."""
    first = raw.split(None, 1)[0] if raw.strip() else ""
    if "state_hash=" in raw:
        return "stamp + state_hash= in place of evidence="
    if OFFSET_STAMP.match(first):
        return "a stamp ending +00:00 instead of Z"
    if len(first) == 20 and first[4] == "-" and first.endswith("Z"):
        return "a stamp, then columns this reader does not take"
    if first.startswith("W") and first[1:].isdigit():
        return "a bare symbol first"
    return "free text"


def reason(why):
    """The reason an unparsed line gave, with the quoted value (a stamp, a symbol) taken out so equal
    reasons count together."""
    return QUOTED.sub("'…'", why)


def report(lines):
    """(parsed, by_why, by_shape, total) over `lines` (ledger.Parsed / ledger.Unparsed)."""
    from mikemol.pathsforward import ledger

    bad = [x for x in lines if isinstance(x, ledger.Unparsed)]
    return (
        len(lines) - len(bad),
        Counter(reason(x.why) for x in bad),
        Counter(shape(x.raw) for x in bad),
        len(lines),
    )


def last_legacy(lines):
    """The 1-based index of the last unparsed line in `lines`, or 0 when every line parses: every line after
    it was written by the structured writer, so it is where the legacy history ends."""
    from mikemol.pathsforward import ledger

    bad = [i for i, x in enumerate(lines, 1) if isinstance(x, ledger.Unparsed)]
    return bad[-1] if bad else 0


_LEGACY = re.compile(
    r"^(?P<stamp>\S+)\s+(?P<kind>\S+)\s+(?P<symbol>\S+)\s+(?P<outcome>\S+)\s+(?P<mechanism>\S+)\s+"
    r'"(?P<note>(?:[^"\\]|\\.)*)"(?P<rest>.*)$'
)
_EVIDENCE_ONLY = re.compile(r"^\s*evidence=(\S+)\s*$")


def rewrite(raw):
    """The current-grammar line for a legacy `raw`, or None when it lacks the legacy columns.

    Each fold keeps every character of the original: a +00:00 stamp becomes the Z stamp it
    names; a symbol that is none of --, W<n>, repo:W<n> (R9, W35-37) becomes -- and moves into
    the note as `[symbol]`; columns after the quoted note (job=, hash=, nudged=) join the note
    after ` | `. The line is returned only when mtools' own parse reads it back as structured."""
    from mikemol.pathsforward import ledger

    m = _LEGACY.match(raw)
    if m is None:
        return None
    stamp = m["stamp"]
    if stamp.endswith("+00:00"):
        stamp = stamp.removesuffix("+00:00") + "Z"
    note = re.sub(r"\\(.)", r"\1", m["note"])
    symbol = m["symbol"] if ledger.is_symbol(m["symbol"]) else ledger.NO_SYMBOL
    if symbol != m["symbol"]:
        note = f"[{m['symbol']}] {note}"
    evidence = ""
    only = _EVIDENCE_ONLY.match(m["rest"])
    if only:
        evidence = only[1]
    elif m["rest"].strip():
        note = f"{note} | {m['rest'].strip()}"
    entry = ledger.Entry(
        m["kind"], symbol, m["outcome"], m["mechanism"], note, evidence
    )
    return _structured(entry, stamp)


def _structured(entry, stamp):
    """`ledger.line(entry, stamp)` when mtools' parse reads it back as structured, else None."""
    from mikemol.pathsforward import ledger

    try:
        out = ledger.line(entry, stamp)
    except ledger.MalformedEntryError:
        return None
    return out if isinstance(ledger.parse(out), ledger.Parsed) else None


_STAMP = re.compile(r"^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(Z|\+00:00)$")


def fold(raw):
    """A legacy line with no quoted note (a hand echo, a second stamp, an unquoted tail) folded whole.

    The first token is the stamp (+00:00 read as Z). When a second stamp follows it, that one is the
    event's own time and the first is kept in the note as `written=`. The next word is the kind (`note`
    when it is not a plain word), the word after it a symbol when it is one (a trailing colon taken
    off), and outcome and mechanism are `legacy`: the whole remaining text, every character, is the
    note, so the fold decides nothing about what the line meant."""
    from mikemol.pathsforward import ledger

    parts = raw.split(None, 1)
    if len(parts) != 2 or not _STAMP.match(parts[0]):
        return None
    stamp = _STAMP.sub(r"\1Z", parts[0])
    rest = parts[1]
    inner = rest.split(None, 1)
    if len(inner) == 2 and _STAMP.match(inner[0]):
        rest = f"{inner[1]}  | written={stamp}"
        stamp = _STAMP.sub(r"\1Z", inner[0])
    words = rest.split(None, 2)
    kind = words[0] if words[0].isalpha() else "note"
    after = rest.split(None, 1)[1] if kind == words[0] and len(words) > 1 else rest
    symbol = ledger.NO_SYMBOL
    if len(words) > 1 and ledger.is_symbol(words[1].rstrip(":")):
        symbol = words[1].rstrip(":")
    return _structured(ledger.Entry(kind, symbol, "legacy", "legacy", after), stamp)


def examples(lines, per_shape=2, width=170):
    """{(shape, why): [raw, ...]}: up to `per_shape` legacy lines for each pair, cut to `width`
    characters, so a rewrite is designed against the lines that exist and not a remembered one."""
    from mikemol.pathsforward import ledger

    out = {}
    for x in lines:
        if isinstance(x, ledger.Unparsed):
            bucket = out.setdefault((shape(x.raw), reason(x.why)), [])
            if len(bucket) < per_shape:
                bucket.append(x.raw[:width])
    return out


def main(argv):
    if argv[1:] not in (["--report"], ["--examples"], ["--plan"], ["--write"]):
        print(f"migrate_ledger: unknown arguments {argv[1:]!r}", file=sys.stderr)
        return 2
    from mikemol.pathsforward import ledger

    lines = ledger.read(Path(LEDGER))
    if not lines:
        print(
            "migrate_ledger: the ledger is empty; the search is broken", file=sys.stderr
        )
        return 2
    if argv[1:] in (["--plan"], ["--write"]):
        texts = Path(LEDGER).read_text(encoding="utf-8").splitlines()
        out, kept = [], []
        for text in texts:
            if isinstance(ledger.parse(text), ledger.Parsed):
                out.append(text)
                continue
            new = rewrite(text) or fold(text)
            if new is None:
                kept.append(text)
            out.append(text if new is None else new)
        legacy = sum(1 for t in texts if not isinstance(ledger.parse(t), ledger.Parsed))
        after = sum(1 for t in out if isinstance(ledger.parse(t), ledger.Parsed))
        print(
            f"migrate_ledger: {legacy - len(kept)} of {legacy} legacy line(s) rewrite; "
            f"{len(kept)} stay as they are; the ledger then parses {after} of {len(out)}",
            file=sys.stderr,
        )
        for raw in kept:
            print(f"kept\t{raw[:140]}")
        if argv[1:] == ["--write"]:
            if len(out) != len(texts):
                print(
                    "migrate_ledger: the line count changed; refusing", file=sys.stderr
                )
                return 1
            tmp = f"{LEDGER}.migrating"
            Path(tmp).write_text("\n".join(out) + "\n", encoding="utf-8")
            os.replace(tmp, LEDGER)
        return 0
    if argv[1:] == ["--examples"]:
        found = examples(lines)
        for (kind, why), raws in sorted(found.items()):
            print(f"{kind} | {why}")
            for raw in raws:
                print(f"    {raw}")
        print(
            f"migrate_ledger: {len(found)} legacy shape/reason pair(s) over "
            f"{sum(1 for x in lines if isinstance(x, ledger.Unparsed))} of {len(lines)} line(s)",
            file=sys.stderr,
        )
        return 0
    parsed, by_why, by_shape, total = report(lines)
    for why, n in by_why.most_common():
        print(f"why\t{n}\t{why}")
    for kind, n in by_shape.most_common():
        print(f"shape\t{n}\t{kind}")
    print(
        f"migrate_ledger: {parsed} of {total} line(s) parse; {total - parsed} legacy; "
        f"the last legacy line is {last_legacy(lines)} of {total}",
        file=sys.stderr,
    )
    return 0


def _selftest():
    from mikemol.pathsforward import ledger

    ok = True

    def chk(label: str, got: object, want: object) -> None:
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    good = '2026-10-17T22:43:55Z  tick  W662  advanced  sweep  "a note"'
    legacy = "2026-09-26T18:51:31Z tick W9 advanced sweep state_hash=v2:abc"
    free = "echo by hand: did a thing"
    lines = [ledger.parse(x) for x in (good, legacy, free)]
    parsed, by_why, by_shape, total = report(lines)
    chk("n of m: one structured line of three parses", (parsed, total), (1, 3))
    chk("the unparsed are counted by reason", sum(by_why.values()), 2)
    chk(
        "the legacy shapes are told apart",
        sorted(by_shape),
        ["free text", "stamp + state_hash= in place of evidence="],
    )
    chk(
        "a +00:00 stamp is its own shape, told from a Z stamp",
        (
            shape("2026-09-20T18:59:08+00:00 tick W9 advanced sweep note"),
            shape("2026-09-20T18:59:08Z tick W9 advanced sweep"),
        ),
        (
            "a stamp ending +00:00 instead of Z",
            "a stamp, then columns this reader does not take",
        ),
    )
    chk(
        "reasons that differ only in the quoted stamp count as one",
        reason("stamp '2026-09-20T18:59:08+00:00' is not x")
        == reason("stamp '2026-09-21T09:30:06+00:00' is not x"),
        True,
    )
    chk(
        "a bare symbol first is its own shape",
        shape("W12 did a thing"),
        "a bare symbol first",
    )
    chk(
        "last_legacy: the index of the last unparsed line, 0 when every line parses",
        (last_legacy(lines), last_legacy(lines[:1])),
        (3, 0),
    )
    chk("an empty ledger would be a refusal, not 0 of 0", report([])[3], 0)
    offset = '2026-09-20T19:38:11+00:00  tick  W4  swept  sweep  "a note"  nudged=x(W3)'
    chk(
        "rewrite: a +00:00 stamp becomes Z and the columns after the note join it",
        rewrite(offset),
        '2026-09-20T19:38:11Z  tick  W4   swept     sweep     "a note | nudged=x(W3)"',
    )
    chk(
        "rewrite: a symbol that is not W<n> becomes -- and moves into the note",
        rewrite('2026-09-25T21:05:00Z  tick  R9  measured  unblock  "n"'),
        '2026-09-25T21:05:00Z  tick  --   measured  unblock   "[R9] n"',
    )
    chk(
        "rewrite: a line without the legacy columns is None, not guessed",
        rewrite("2026-09-21T02:30:49+00:00  tick W12/W14: re-armed d8d6d0b5"),
        None,
    )
    chk(
        "fold: a hand echo keeps every word of its text and parses",
        fold("2026-09-21T02:30:49+00:00  tick W12: re-armed d8d6"),
        '2026-09-21T02:30:49Z  tick  W12  legacy    legacy    "W12: re-armed d8d6"',
    )
    two = '2026-09-22T13:45:56+00:00  2026-09-22T16:00:00Z  tick  W61 advanced  "x"'
    chk(
        "fold: a second stamp is the event time and the first is kept as written=",
        fold(two),
        "2026-09-22T16:00:00Z  tick  W61  legacy    legacy    "
        '"W61 advanced  \\"x\\"  | written=2026-09-22T13:45:56Z"',
    )
    chk(
        "fold: text that does not start with a stamp is None",
        fold("echo by hand"),
        None,
    )
    live = Path(LEDGER).read_text(encoding="utf-8").splitlines()
    chk(
        "every live line parses, or rewrites, or folds (nothing stays legacy)",
        all(
            isinstance(ledger.parse(t), ledger.Parsed) or (rewrite(t) or fold(t))
            for t in live
        ),
        True,
    )
    real = ledger.read(Path(LEDGER)) if os.path.isfile(LEDGER) else []
    chk("the live ledger has lines to read (n of m, never 0 of 0)", len(real) > 0, True)
    print("migrate_ledger selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
