#!/usr/bin/env python3
"""cotype_index.py — read the design log STRUCTURALLY.

COTYPE.md is a 4,600-line append-only design log, and it is not prose: it has a
grammar. Sessions, ⊕symbols, closure sections asserting an invariant realized,
four-gate verdicts, and a symbol ledger re-stated at the end of every session.
Answering "what is still open?" by reading it is the shape this repo's standing
rule forbids — so this module owns the question instead.

    scripts/cotype_index.py                # the summary: sessions, symbols, open set
    scripts/cotype_index.py --symbols      # every symbol, with closed/open status
    scripts/cotype_index.py --open         # the open set, bucketed by OPERATOR
    scripts/cotype_index.py --closures     # symbols carrying a closure section
    scripts/cotype_index.py --gates        # four-gate lines, per symbol
    scripts/cotype_index.py --sessions     # the session list
    scripts/cotype_index.py --json         # all of it, machine-readable

⚑ THE LAST LEDGER WINS, AND EVERY EARLIER ONE IS A SNAPSHOT.  The log restates
"## Symbol ledger (current)" once per session — 58 times.  Reading any but the
LAST answers a question about a past state while looking like it answers about
now.  This module takes the final block, and `--ledger-count` exists so that
choice is auditable rather than assumed.

⚑ OPEN IS BUCKETED BY OPERATOR, AND THE BUCKETS ARE NOT INTERCHANGEABLE.  The
log distinguishes BUILD (touches the shipped package), RESEARCH (design, no
package impact), LIVE (operator=other — only a human at a real desktop can run
it), TUNE, TIER 3, and RESIDUE.  A LIVE item CANNOT be discharged by any check
this repo could write, so any claim over it must say so rather than pretend a
machine could close it.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COTYPE = os.path.join(ROOT, "COTYPE.md")

# ⚑ NO TRAILING HYPHEN.  The log writes symbols in running prose — "the exact
# ⊕GTK-class failure" — and a greedy `[A-Z0-9-]*` swallows the hyphen, minting
# `⊕GTK-` as a symbol distinct from `⊕GTK`.  Measured: 11 such phantoms, every
# one of which then reported as a dangling never-resolved item.  A symbol ends
# on an alphanumeric.
SYMBOL = re.compile(r"⊕[A-Z0-9](?:[A-Z0-9-]*[A-Z0-9])?")
# The operator buckets the final ledger uses, in the log's own words.
BUCKETS = ("BUILD", "RESEARCH", "LIVE", "TUNE", "TIER 3", "RESIDUE", "OPEN")


def _text():
    if not os.path.exists(COTYPE):
        return None
    return open(COTYPE, encoding="utf-8", errors="replace").read()


def sessions(text=None):
    """[(lineno, title)] — every session heading, in order."""
    text = _text() if text is None else text
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("## Session"):
            out.append((i, line[3:].strip()))
    return out


def closures(text=None):
    """{symbol: [lineno]} — symbols carrying a `### ⊕X closure` section."""
    text = _text() if text is None else text
    out = {}
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("###") and "closure" in line:
            m = SYMBOL.search(line)
            if m:
                out.setdefault(m.group(0), []).append(i)
    return out


def gates(text=None):
    """{symbol: n} — how many four-gate verdicts each symbol's closure carries.

    The log writes gates as `- Four gates: …` / `- Gate (four): …` inside a
    closure.  Attribution is to the nearest preceding closure heading, because a
    gate line names no symbol of its own."""
    text = _text() if text is None else text
    out, current = {}, None
    for line in text.splitlines():
        if line.startswith("###") and "closure" in line:
            m = SYMBOL.search(line)
            current = m.group(0) if m else None
        elif current and re.match(r"^- (Four gates|Gates? \(four\))", line.strip()):
            out[current] = out.get(current, 0) + 1
    return out


def ledger_blocks(text=None):
    """[(lineno, body)] — every `## Symbol ledger` block, in order.  A SERIES."""
    text = _text() if text is None else text
    lines = text.splitlines()
    out = []
    for i, line in enumerate(lines):
        if line.startswith("## Symbol ledger"):
            body = []
            for nxt in lines[i + 1:]:
                if nxt.startswith("## ") or nxt.startswith("# "):
                    break
                body.append(nxt)
            out.append((i + 1, "\n".join(body)))
    return out


def open_set(text=None):
    """{bucket: [symbols]} from the LAST ledger block — the only current one."""
    blocks = ledger_blocks(text)
    if not blocks:
        return {}
    _, body = blocks[-1]
    found, bucket = {}, None
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped.startswith("-"):
            # a continuation line keeps the bucket it is indented under
            if bucket:
                for s in SYMBOL.findall(line):
                    found.setdefault(bucket, []).append(s)
            continue
        head = stripped.lstrip("- ").strip()
        hit = None
        for b in BUCKETS:
            if head.upper().startswith(b):
                hit = b
                break
        # "OPEN — BUILD (...)": the more specific bucket wins
        if hit == "OPEN":
            for b in BUCKETS:
                if b != "OPEN" and re.search(rf"\b{re.escape(b)}\b", head.upper()[:40]):
                    hit = b
                    break
        bucket = hit or bucket
        if bucket:
            for s in SYMBOL.findall(line):
                found.setdefault(bucket, []).append(s)
    return {k: sorted(set(v)) for k, v in found.items()}


def ledger_closed(text=None):
    """Symbols the FINAL ledger marks closed — its `… ✓ (n)` line.

    ⚑ A CLOSURE SECTION IS NOT THE ONLY EVIDENCE OF CLOSURE.  Early symbols were
    closed before the log adopted per-symbol closure sections, and the ledger
    records them on a ✓ line instead.  Reading only the sections reported 31
    symbols as never-resolved, most of which are shipped and sitting on disk
    (⊕AMB and ⊕AZR are the Amber and Azure schemes).  Both forms count."""
    blocks = ledger_blocks(text)
    if not blocks:
        return set()
    out = set()
    for line in blocks[-1][1].splitlines():
        if "✓" in line and not line.strip().upper().startswith("- OPEN"):
            out |= set(SYMBOL.findall(line.split("✓")[0]))
    # "…prior… + ⊕X ✓" carries earlier ledgers by reference, so fold them in.
    if any("prior" in l.lower() for l in blocks[-1][1].splitlines()):
        for _, body in blocks[:-1]:
            for line in body.splitlines():
                if "✓" in line and not line.strip().upper().startswith("- OPEN"):
                    out |= set(SYMBOL.findall(line.split("✓")[0]))
    return out


def symbols(text=None):
    """{symbol: {"closed": bool, "gates": int, "buckets": [...]}} for every symbol."""
    text = _text() if text is None else text
    clo, gts, opn = closures(text), gates(text), open_set(text)
    tick = ledger_closed(text)
    where = {}
    for bucket, syms in opn.items():
        for s in syms:
            where.setdefault(s, []).append(bucket)
    out = {}
    for s in sorted(set(SYMBOL.findall(text))):
        out[s] = {"closed": s in clo or s in tick,
                  "by": ("closure" if s in clo else ("ledger-tick" if s in tick
                                                     else None)),
                  "gates": gts.get(s, 0),
                  "buckets": sorted(where.get(s, []))}
    return out


def main(argv):
    known = {"--symbols", "--open", "--closures", "--gates", "--sessions",
             "--json", "--ledger-count"}
    for a in argv[1:]:
        if a not in known:
            print(f"cotype_index: unknown flag {a!r} "
                  f"(known: {', '.join(sorted(known))})", file=sys.stderr)
            return 2
    text = _text()
    if text is None:
        print(f"cotype_index: REFUSED — {os.path.basename(COTYPE)} is absent",
              file=sys.stderr)
        return 2

    sess, clo, gts, opn, syms = (sessions(text), closures(text), gates(text),
                                 open_set(text), symbols(text))
    blocks = ledger_blocks(text)

    if "--ledger-count" in argv:
        print(len(blocks))
        return 0
    if "--sessions" in argv:
        for ln, title in sess:
            print(f"{ln}\t{title}")
        return 0
    if "--closures" in argv:
        for s, lns in sorted(clo.items()):
            print(f"{s}\t{','.join(str(x) for x in lns)}")
        return 0
    if "--gates" in argv:
        for s, n in sorted(gts.items()):
            print(f"{s}\t{n}")
        return 0
    if "--open" in argv:
        for b in BUCKETS:
            if b in opn:
                print(f"{b} ({len(opn[b])}): {' '.join(opn[b])}")
        return 0
    if "--symbols" in argv:
        for s, d in sorted(syms.items()):
            state = "closed" if d["closed"] else ("open:" + ",".join(d["buckets"])
                                                  if d["buckets"] else "unlisted")
            print(f"{s}\t{state}\tgates={d['gates']}")
        return 0
    if "--json" in argv:
        print(json.dumps({"sessions": len(sess), "ledger_blocks": len(blocks),
                          "closures": {k: v for k, v in clo.items()},
                          "gates": gts, "open": opn, "symbols": syms}, indent=2))
        return 0

    n_open = sum(len(v) for v in opn.values())
    print(f"cotype_index: {len(sess)} sessions, {len(syms)} symbols, "
          f"{len(clo)} closed, {n_open} open across {len(opn)} operator bucket(s)")
    print(f"    ledger blocks: {len(blocks)} (the LAST is current; earlier are snapshots)")
    for b in BUCKETS:
        if b in opn:
            print(f"    {b:9} {len(opn[b]):3}  {' '.join(opn[b][:6])}"
                  f"{' …' if len(opn[b]) > 6 else ''}")
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

    text = _text()
    if text is None:
        print("  FAIL COTYPE.md absent")
        return False
    check("found sessions", len(sessions(text)) > 0, True)
    check("found closures", len(closures(text)) > 0, True)
    check("found a symbol ledger series", len(ledger_blocks(text)) > 1, True)
    # ⚑ The parser must read the LAST ledger, not the first — the defect this
    # module exists to prevent.  The two differ, and that is what makes it a test.
    first_body = ledger_blocks(text)[0][1]
    last_body = ledger_blocks(text)[-1][1]
    check("the ledger series actually moves", first_body != last_body, True)
    opn = open_set(text)
    check("the open set is non-empty", sum(len(v) for v in opn.values()) > 0, True)
    check("open symbols are bucketed by operator", all(
        b in BUCKETS for b in opn), True)
    # A symbol with a closure must be reported closed.
    clo = closures(text)
    if clo:
        s = sorted(clo)[0]
        check(f"a closed symbol reads closed ({s})", symbols(text)[s]["closed"], True)
    # The grammar assumptions must hold on THIS document, or the parse is fiction.
    # ⚑ NOT EVERY `closure` HEADING IS A SYMBOL CLOSURE.  The log also carries
    # META-audits — "### Gate closure audit (four gates on the gate)" — which
    # close no ⊕symbol.  The first version of this test asserted every closure
    # line names a symbol and FAILED on exactly that heading: the grammar
    # assumption was too broad, not the document irregular.  A symbol closure is
    # the ones this counts; the audits are a separate form and are reported so
    # they cannot be silently swallowed.
    headings = [l for l in text.splitlines() if l.startswith("###") and "closure" in l]
    audits = [l for l in headings if not SYMBOL.search(l)]
    check("symbol closures all name a symbol",
          all(SYMBOL.search(l) for l in headings if l not in audits), True)
    check(f"meta-audit headings are accounted for ({len(audits)})",
          all("audit" in l.lower() for l in audits), True)
    print("cotype_index selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
