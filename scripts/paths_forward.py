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
    paths_forward.py --selftest   prove --check can SEE a vanished symbol, and --payload
                                  carries the preamble (and only when one is set)
    paths_forward.py --preamble-set FILE | --preamble-show | --preamble-clear
                                  the standing rules --payload emits verbatim after
                                  its header (swarm discipline, per-tick opening cmd)
    --state PATH                  operate on a copy (mirror + ledger follow it)

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


def load(path: str | None = None) -> dict:
    with open(path or STATE, encoding="utf-8") as fh:
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


class PayloadOverBudget(RuntimeError):
    """The payload cannot be trimmed to fit, and pretending otherwise would arm
    the loop with a prompt the scheduler may reject or the tick may not read."""


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
    ]
    # ⚑ THE PREAMBLE IS DECLARED STATE, emitted verbatim after the header. Before
    # this field existed the standing rules (swarm discipline, the per-tick opening
    # command, "SWARM HELD because…") lived only in a hand-pasted prompt, so a
    # re-arm from --payload silently DROPPED them. Set it with --preamble-set.
    pre = state.get("preamble") or []
    if isinstance(pre, str):
        pre = pre.splitlines()
    pre_lines = ["preamble:"] + [f"  {l}" for l in pre] if pre else []
    lines.append("waypoints:")
    live, done = [], []
    for w in state["waypoints"]:
        if w["status"] == "done":
            done.append(w["symbol"])
            continue
        # ⚑ A STRING IS AN ITERABLE OF CHARACTERS, which is why this printed
        # `blocked_on=m,i,k,e,m,o,l` for 5 ticks: blocked_on is declared a LIST and
        # W12 carries a bare str, so join() succeeded and produced nonsense. A
        # silent success on the wrong type is worse than a TypeError.
        on = w["blocked_on"]
        on = [on] if isinstance(on, str) else list(on)
        b = f" blocked_on={','.join(on)}({w['blocked_kind']})" if on else ""
        live.append(
            f"  {w['symbol']} [{w['status']}]{b} ticks_blocked={w['ticks_blocked']} :: {w['title']}\n"
            f"      next: {w['next_bounded_step']}\n"
            f"      evidence: {w['evidence'].splitlines()[0] if w['evidence'] else '-'}"
        )
    # ⚑ A DONE WAYPOINT COSTS A LINE, NOT A STANZA. Measured 2026-09-22: the full
    # payload was 45.8 KB against a 6 KB budget, because 46 of 61 waypoints were
    # `done` and each carried its title, its next step and its evidence. Status is
    # recomputed from the checks every tick anyway (there is no open/closed field),
    # so a done item's PROSE is the one thing the payload never needs — only its
    # symbol, so that §8's coverability holds and no symbol vanishes.
    done_line = (f"done ({len(done)}): {', '.join(done)}" if done else "")
    residue = [f"  {r['symbol']}: {r['reason']}" for r in state["residue"]]

    def render(detail_n, with_evidence, with_residue, with_preamble=True):
        # ⚑ ONLY THE TOP ITEMS NEED THEIR STEP. A tick advances exactly ONE
        # waypoint (§4.4), so the prose that must survive the budget is the prose
        # of the item that will be worked. The rest need identity, status and
        # blocked-on — enough to re-sort and enough that no symbol vanishes.
        # ⚑ A COLLAPSED LINE IS CLIPPED, because these titles are PARAGRAPHS: W58's
        # carries its whole three-branch spec. Measured 2026-09-22 — 17 live
        # waypoints came to 15.7 KB with only ONE step rendered, all of it title.
        # The payload's job is to force the queue into the tick's context, not to
        # be the queue; state_path is on line 2 and the tick is told to read it.
        def clip(stanza):
            head = stanza.splitlines()[0]
            return head if len(head) <= 160 else head[:157] + "..."

        head = lines[:-1] + (pre_lines if with_preamble else []) + lines[-1:]
        out = head + live[:detail_n] + [clip(l) for l in live[detail_n:]]
        if done_line:
            out.append("  " + done_line)
        if with_residue and residue:
            out += ["residue:"] + residue
        text = "\n".join(out)
        if not with_evidence:
            text = "\n".join(l for l in text.splitlines() if not l.startswith("      evidence"))
        return text

    # ⚑ THE LADDER MUST REPORT WHETHER IT SUCCEEDED. The previous version dropped
    # residue, then evidence, then RETURNED whatever it had — over budget, with
    # `truncated=true` attached. A payload that announces it was trimmed and is
    # still too large is a gate that accepts `--queit` and exits 0.
    n = len(live)
    rungs = [((n, True, True), []),
             ((n, True, False), ["residue"]),
             ((n, False, False), ["residue", "evidence"]),
             ((5, False, False), ["residue", "evidence", "steps-below-5"]),
             ((2, False, False), ["residue", "evidence", "steps-below-2"]),
             ((1, False, False), ["residue", "evidence", "steps-below-1"])]
    # The preamble is the LAST thing sacrificed, and its loss is named with its
    # line count so the tick knows standing rules are missing, not absent.
    if pre:
        rungs.append(((1, False, False, False),
                      ["residue", "evidence", "steps-below-1", f"preamble({len(pre)}-lines)"]))
    for (flags, dropped) in rungs:
        text = render(*flags)
        if len(text) <= PAYLOAD_BUDGET:
            if dropped:
                text += (f"\ntruncated=true dropped={','.join(dropped)}"
                         f" — read the file for the rest.")
            return text
    raise PayloadOverBudget(
        f"payload is {len(text)} bytes even with ONE waypoint's step; the budget is "
        f"{PAYLOAD_BUDGET}. {len(live)} live waypoint(s) — the top item's "
        f"next_bounded_step alone does not fit, so shorten it or split the waypoint.")


def queue(state: dict) -> str:
    rows = []
    for i, w in enumerate(state["waypoints"], 1):
        rows.append(f"{i:>2}. {w['symbol']:<4} {w['status']:<8} {w['title']}  — {w.get('rank_reason', '')}")
    return "\n".join(rows)


def save(state: dict, path: str | None = None) -> None:
    # ⚑ resolved at CALL time: a `path=STATE` default binds at def time, so
    # --state would load the temp copy and write the live file.
    with open(path or STATE, "w", encoding="utf-8") as fh:
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


WAYPOINT_FIELDS = ("symbol", "title", "status", "enables", "touches", "blocked_on", "blocked_kind",
                   "rank_reason", "next_bounded_step", "evidence", "issued_at", "last_worked", "ticks_blocked")


def add(state: dict, title: str, kvs: list[str]) -> str:
    """Mint the next symbol (counter only ever increments) and append a ready waypoint.

    ⚑ VALIDATE BEFORE MINTING. This once saved the bare waypoint and THEN applied the
    key=values, so a refused key (2026-09-22: `mechanism=`) left a half-written W54 on
    disk and the retry minted W55 as its duplicate — a burned symbol with a partial
    record, which the coverage check cannot tell from an honest one."""
    bad = [kv.partition("=")[0] for kv in kvs if kv.partition("=")[0] not in WAYPOINT_FIELDS]
    if bad:
        raise SystemExit(f"--add refused, nothing minted: unknown field(s) {bad}; fields: {', '.join(WAYPOINT_FIELDS)}")
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


def drop(state: dict, sym: str, reason: str) -> None:
    """§5 `drop W7 <reason>` — move a waypoint to residue; the reason is required and
    the symbol stays claimed forever (never reused, never renumbered)."""
    if not reason.strip():
        raise SystemExit(f"drop {sym}: a reason is required")
    w = find(state, sym)
    if w.get("dropped_at"):
        raise SystemExit(f"{sym} is already residue")
    state["waypoints"] = [x for x in state["waypoints"] if x["symbol"] != sym]
    state.setdefault("residue", []).append({"symbol": sym, "title": w.get("title", ""), "dropped_at": now(),
                                            "reason": reason, "recoverable": True})
    save(state)


def ledger(line: str) -> None:
    with open(os.path.splitext(STATE)[0] + ".ledger", "a", encoding="utf-8") as fh:
        fh.write(f"{now()}  {line}\n")


def selftest() -> int:
    good = {"counter": 2, "project_root": "/x", "waypoints": [{"symbol": "W1"}], "residue": [{"symbol": "W2", "reason": "r"}]}
    bad = {"counter": 3, "project_root": "/x", "waypoints": [{"symbol": "W1"}], "residue": [{"symbol": "W2", "reason": ""}]}
    if check(good):
        print("selftest: FAIL — clean state reported problems", check(good)); return 1
    p = check(bad)
    if not any("W3" in x for x in p) or not any("without a reason" in x for x in p):
        print("selftest: FAIL — could not see a vanished symbol / reasonless drop", p); return 1
    # --payload carries the preamble (a), omits it when absent (b), names the job (d).
    wp = {"symbol": "W1", "title": "t", "status": "ready", "blocked_on": [], "blocked_kind": None,
          "ticks_blocked": 0, "next_bounded_step": "s", "evidence": "e"}
    base = {"counter": 1, "project_root": "/x", "job_id": "job-SELFTEST", "waypoints": [wp], "residue": []}
    pre = ["swarm discipline: RULE-ONE", "open with `python3 scripts/check_marquee_host.py`",
           "SWARM HELD because RULE-THREE"]
    with_pre = payload(dict(base, preamble=pre))
    missing = [l for l in pre if l not in with_pre]
    if missing:
        print("selftest: FAIL — payload dropped preamble line(s)", missing); return 1
    without = payload(base)
    if "preamble:" in without or any(l in without for l in pre):
        print("selftest: FAIL — payload without a preamble emitted one"); return 1
    if "job_id=job-SELFTEST" not in with_pre:
        print("selftest: FAIL — payload does not name the current job_id"); return 1
    # A preamble too large to keep must be NAMED as dropped, never silently lost.
    huge = [f"rule {i} " + "x" * 80 for i in range(100)]
    t = payload(dict(base, preamble=huge))
    if f"preamble({len(huge)}-lines)" not in t or "rule 0 " in t:
        print("selftest: FAIL — an over-budget preamble was not reported in truncated="); return 1
    # (c) an unknown flag is refused, not run.
    try:
        # beside a VALID mode, so the refusal is for the unknown flag and not
        # for a missing required one (which is what a bare `--queit` measured).
        main(["--selftest", "--queit"])
        print("selftest: FAIL — unknown flag --queit was accepted"); return 1
    except SystemExit as e:
        if e.code != 2:
            print(f"selftest: FAIL — unknown flag exited {e.code}, not 2"); return 1
    print("selftest: OK — --check sees a vanished symbol and a reasonless drop; --payload carries "
          f"{len(pre)} of {len(pre)} preamble lines, none when unset, names job_id, reports a "
          "truncated preamble; unknown flags refused"); return 0


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
    g.add_argument("--drop", nargs=2, metavar=("SYMBOL", "REASON"), help="§5 move a waypoint to residue (reason required)")
    g.add_argument("--preamble-set", metavar="FILE", help="store FILE's lines as the payload preamble")
    g.add_argument("--preamble-show", action="store_true", help="print the stored preamble")
    g.add_argument("--preamble-clear", action="store_true", help="remove the stored preamble")
    ap.add_argument("--state", metavar="PATH", help="operate on PATH instead of .claude/paths-forward.json")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.state:
        global STATE, MIRROR  # siblings (.md mirror, .ledger) follow the state file
        STATE = os.path.abspath(a.state)
        MIRROR = os.path.splitext(STATE)[0] + ".md"
    state = load(STATE)
    if a.preamble_set:
        with open(a.preamble_set, encoding="utf-8") as fh:
            pre = fh.read().splitlines()
        if not any(l.strip() for l in pre):
            print(f"--preamble-set REFUSED: {a.preamble_set} has 0 non-blank lines (use --preamble-clear)")
            return 1
        state["preamble"] = pre; save(state, STATE)
        print(f"preamble set: {len(pre)} line(s); hash={state_hash(state)}")
        return 0
    if a.preamble_show:
        pre = state.get("preamble") or []
        print(f"preamble: {len(pre)} line(s)")
        for l in pre:
            print(f"  {l}")
        return 0
    if a.preamble_clear:
        n = len(state.pop("preamble", None) or []); save(state, STATE)
        print(f"preamble cleared ({n} line(s) removed)")
        return 0
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
    elif a.drop:
        drop(state, a.drop[0], a.drop[1]); print(f"{a.drop[0]} -> residue; hash={state_hash(load())}")
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
