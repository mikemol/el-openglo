#!/usr/bin/env python3
"""paths_forward — the ONE reader/writer of `.claude/paths-forward.json`.

The paths-forward loop (skill: paths-forward-loop) keeps a symbol-addressable queue of
waypoints that a cron tick re-derives and advances.  Everything the tick needs from the
file goes through here, so the hash, the mirror and the payload are computed by a
program rather than re-derived per turn:

    paths_forward.py --hash       sha256 over the `waypoints` array (drift detection)
    paths_forward.py --render     regenerate .claude/paths-forward.md (derived mirror)
    paths_forward.py --payload    the cron prompt: queue digest + state_hash, budgeted
    paths_forward.py --queue      human one-screen view of the order
    paths_forward.py --check      every symbol ever issued resolves (charter: coverable)
    paths_forward.py --selftest   prove --check can SEE a vanished symbol

WEAKNESS: this tool proves the FILE is coherent.  It does not prove any waypoint's
`evidence` still holds — that is the tick's job, against the worklist gate, which is
the actual status.  A waypoint here is a pointer into that gate, never a second status.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, ".claude", "paths-forward.json")
MIRROR = os.path.join(ROOT, ".claude", "paths-forward.md")
PAYLOAD_BUDGET = 6000  # chars; over it, residue reasons go first, then evidence

ORDER = {"working": 0, "ready": 1, "blocked": 2, "done": 3, "dropped": 4}


def load(path: str = STATE) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def state_hash(state: dict) -> str:
    blob = json.dumps(state["waypoints"], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def check(state: dict) -> list[str]:
    """Coverable: W1..W<counter> each resolve to a waypoint or a residue entry."""
    live = {w["symbol"] for w in state["waypoints"]}
    res = {r["symbol"] for r in state["residue"]}
    problems = []
    for n in range(1, state["counter"] + 1):
        s = f"W{n}"
        if s not in live and s not in res:
            problems.append(f"{s}: issued (counter={state['counter']}) but in neither waypoints nor residue")
        if s in live and s in res:
            problems.append(f"{s}: both live and residue")
    for r in state["residue"]:
        if not r.get("reason"):
            problems.append(f"{r['symbol']}: dropped without a reason")
    return problems


def render(state: dict) -> str:
    out = [
        "<!-- DERIVED. Regenerated every tick by scripts/paths_forward.py --render.",
        "     Edits here vanish; edit .claude/paths-forward.json (or tell the loop). -->",
        f"# paths-forward — {os.path.basename(state['project_root'])}",
        "",
        f"heartbeat {state.get('heartbeat')} · job `{state.get('job_id')}` · "
        f"counter {state['counter']} · hash `{state_hash(state)}`",
        "",
        "| # | status | title | blocked on | next bounded step |",
        "|---|---|---|---|---|",
    ]
    for w in state["waypoints"]:
        out.append(
            f"| {w['symbol']} | {w['status']} | {w['title']} | "
            f"{', '.join(w['blocked_on']) or '—'} | {w['next_bounded_step']} |"
        )
    out += ["", "## evidence", ""]
    for w in state["waypoints"]:
        out.append(f"- **{w['symbol']}** — {w['evidence']}")
    out += ["", "## residue", ""]
    for r in state["residue"]:
        out.append(f"- **{r['symbol']}** ({r['dropped_at']}) {r['title']}: {r['reason']}")
    if not state["residue"]:
        out.append("- (none)")
    return "\n".join(out) + "\n"


def payload(state: dict) -> str:
    lines = [
        "[paths-forward tick] Invoke the paths-forward-loop skill and run ONE tick (§4).",
        f"state_path={STATE}",
        f"project_root={state['project_root']}",
        f"counter={state['counter']} state_hash={state_hash(state)} "
        f"generated_at={datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "Run `python3 scripts/paths_forward.py --hash` first; if it differs from state_hash the FILE wins.",
        "Ground truth is `python3 scripts/worklist_gate.py` — a waypoint is done when its check goes green.",
        f"Re-arm when the hash changes: CronCreate a fresh job from `--payload`, verify with CronList, "
        f"THEN CronDelete the predecessor (job_id={state.get('job_id')}).",
        "waypoints:",
    ]
    for w in state["waypoints"]:
        b = f" blocked_on={','.join(w['blocked_on'])}({w['blocked_kind']})" if w["blocked_on"] else ""
        lines.append(
            f"  {w['symbol']} [{w['status']}]{b} ticks_blocked={w['ticks_blocked']} :: {w['title']}\n"
            f"      next: {w['next_bounded_step']}\n"
            f"      evidence: {w['evidence'].splitlines()[0] if w['evidence'] else '-'}"
        )
    residue = [f"  {r['symbol']}: {r['reason']}" for r in state["residue"]]
    text = "\n".join(lines + (["residue:"] + residue if residue else []))
    truncated = []
    if len(text) > PAYLOAD_BUDGET and residue:
        truncated.append("residue")
        text = "\n".join(lines)
    if len(text) > PAYLOAD_BUDGET:
        truncated.append("evidence")
        text = "\n".join(l for l in text.splitlines() if not l.startswith("      evidence"))
    if truncated:
        text += f"\ntruncated=true dropped={','.join(truncated)} — read the file for the rest."
    return text


def queue(state: dict) -> str:
    rows = []
    for i, w in enumerate(state["waypoints"], 1):
        rows.append(f"{i:>2}. {w['symbol']:<4} {w['status']:<8} {w['title']}  — {w.get('rank_reason', '')}")
    return "\n".join(rows)


def save(state: dict, path: str = STATE) -> None:
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def find(state: dict, sym: str) -> dict:
    for w in state["waypoints"]:
        if w["symbol"] == sym:
            return w
    for r in state["residue"]:
        if r["symbol"] == sym:
            raise SystemExit(f"{sym} is residue: {r['reason']}")
    raise SystemExit(f"{sym}: not issued (counter={state['counter']})")


def lock(state: dict, holder: str) -> int:
    """§4.1 — take the lock; exit 3 (silently, for the tick) if a live holder exists."""
    lk = state.get("lock")
    if lk:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(lk["taken_at"])).total_seconds()
        if age < 1800:
            print(f"locked by {lk['holder']} since {lk['taken_at']} ({age:.0f}s)")
            return 3
        print(f"taking over stale lock from {lk['holder']} ({age:.0f}s)")
    state["lock"] = {"holder": holder, "taken_at": now()}
    save(state)
    return 0


def set_fields(state: dict, sym: str, kvs: list[str]) -> None:
    """--set W1 status=done evidence='...' — JSON-typed values where they parse."""
    w = find(state, sym)
    for kv in kvs:
        k, _, v = kv.partition("=")
        if k not in w:
            raise SystemExit(f"{sym} has no field {k!r}; fields: {', '.join(w)}")
        try:
            w[k] = json.loads(v)
        except json.JSONDecodeError:
            w[k] = v
    w["last_worked"] = now()
    save(state)


def add(state: dict, title: str, kvs: list[str]) -> str:
    """Mint the next symbol (counter only ever increments) and append a ready waypoint."""
    state["counter"] += 1
    sym = f"W{state['counter']}"
    w = {"symbol": sym, "title": title, "status": "ready", "enables": [], "touches": [],
         "blocked_on": [], "blocked_kind": None, "rank_reason": "", "next_bounded_step": "",
         "evidence": "", "issued_at": now(), "last_worked": None, "ticks_blocked": 0}
    state["waypoints"].append(w)
    save(state)
    if kvs:
        set_fields(state, sym, kvs)
    return sym


def ledger(line: str) -> None:
    with open(os.path.join(ROOT, ".claude", "paths-forward.ledger"), "a", encoding="utf-8") as fh:
        fh.write(f"{now()}  {line}\n")


def selftest() -> int:
    good = {"counter": 2, "project_root": "/x", "waypoints": [{"symbol": "W1"}], "residue": [{"symbol": "W2", "reason": "r"}]}
    bad = {"counter": 3, "project_root": "/x", "waypoints": [{"symbol": "W1"}], "residue": [{"symbol": "W2", "reason": ""}]}
    if check(good):
        print("selftest: FAIL — clean state reported problems", check(good)); return 1
    p = check(bad)
    if not any("W3" in x for x in p) or not any("without a reason" in x for x in p):
        print("selftest: FAIL — could not see a vanished symbol / reasonless drop", p); return 1
    print("selftest: OK — --check sees a vanished symbol and a reasonless drop"); return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    g = ap.add_mutually_exclusive_group(required=True)
    for f in ("hash", "render", "payload", "queue", "check", "selftest"):
        g.add_argument(f"--{f}", action="store_true")
    g.add_argument("--lock", metavar="HOLDER", help="§4.1 take the tick lock (exit 3 if held <30m)")
    g.add_argument("--unlock", action="store_true")
    g.add_argument("--armed", metavar="JOB_ID", help="record job_id + heartbeat after CronList verifies")
    g.add_argument("--set", nargs="+", metavar=("SYMBOL", "key=value"), help="update a waypoint's fields")
    g.add_argument("--ledger", metavar="LINE", help="append one line (timestamp is prepended)")
    g.add_argument("--add", nargs="+", metavar=("TITLE", "key=value"), help="mint the next W<n> as a ready waypoint")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    state = load()
    if a.lock:
        return lock(state, a.lock)
    if a.unlock:
        state["lock"] = None; save(state); print("unlocked")
    elif a.armed:
        state["job_id"] = a.armed; state["heartbeat"] = now(); save(state); print(f"armed job_id={a.armed}")
    elif a.set:
        set_fields(state, a.set[0], a.set[1:]); print(f"{a.set[0]} updated; hash={state_hash(state)}")
    elif a.ledger:
        ledger(a.ledger); print("ledger appended")
    elif a.add:
        sym = add(state, a.add[0], a.add[1:]); print(f"{sym} added; hash={state_hash(load())}")
    elif a.hash:
        print(state_hash(state))
    elif a.render:
        with open(MIRROR, "w", encoding="utf-8") as fh:
            fh.write(render(state))
        print(f"rendered {MIRROR}")
    elif a.payload:
        print(payload(state))
    elif a.queue:
        print(queue(state))
    elif a.check:
        p = check(state)
        n = state["counter"]
        if p:
            print(f"paths_forward --check: REFUSED — {len(p)} of {n} symbol(s) do not resolve:")
            for x in p:
                print("    " + x)
            return 1
        print(f"paths_forward --check: OK — {n} of {n} symbols resolve")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
