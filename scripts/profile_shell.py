#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""profile_shell.py — where plasmashell's CPU goes, per THREAD, over time.

⚑ WHY (operator, 2026-10-11: the marquee "slows my desktop dramatically ... for some time";
left installed overnight so there is something to read). A shell at 89 % CPU names no
culprit by itself; the SPLIT does: the GUI thread (JS: the backdrop's sample()/integrate(),
bindings), the render thread (scene-graph work: the pips, the halo), the QML engine
thread, or the GPU driver's helpers. This samples /proc/<pid>/task/*/stat on an interval
and writes one JSON line per sample to --out, structure only (a thread name and a
percentage, never a notification's text; the journal ships elsewhere).

    scripts/profile_shell.py --out /var/tmp/el-openglo-profile/shell.jsonl   # until killed
    scripts/profile_shell.py --out F --interval 5 --duration 3600
    scripts/profile_shell.py --report F       # the per-thread summary of a recorded run
    scripts/profile_shell.py --selftest

WEAKNESS: sampling /proc says WHICH thread burns CPU, not which function. The kernel
denies ptrace on the shell (measured: eu-stack, Operation not permitted), so there is no
stack here; the thread split plus the marquee's own trace (check_marquee_host.py) is the
evidence, and a per-function profile needs a run under a profiler the operator starts.
A thread that starts and ends between two samples is invisible.
"""

import json
import os
import sys
import time

CLK = os.sysconf("SC_CLK_TCK")
FLAGS = {
    "--pid",
    "--interval",
    "--out",
    "--duration",
    "--report",
    "--holders",
    "--selftest",
}


def find_pid(name="plasmashell"):
    """The pid of the newest process whose comm is `name`, or None."""
    found = []
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            with open(f"/proc/{entry}/comm") as fh:
                if fh.read().strip() == name:
                    found.append(int(entry))
        except OSError:
            continue
    return max(found) if found else None


def read_threads(pid, proc="/proc"):
    """{tid: (comm, cpu_ticks)} for every thread of `pid` (utime + stime)."""
    out = {}
    base = f"{proc}/{pid}/task"
    for tid in os.listdir(base):
        try:
            with open(f"{base}/{tid}/stat") as fh:
                raw = fh.read()
        except OSError:
            continue  # the thread ended between the listing and the read
        # comm is parenthesised and may hold spaces: split at the LAST ")"
        head, _, tail = raw.rpartition(")")
        comm = head.partition("(")[2]
        fields = tail.split()
        out[int(tid)] = (comm, int(fields[11]) + int(fields[12]))
    return out


def rss_kb(pid, proc="/proc"):
    with open(f"{proc}/{pid}/status") as fh:
        for line in fh:
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    return None


def delta(before, after, dt, floor=1.0):
    """[{tid, comm, pct}] for threads whose CPU rose by at least `floor` percent of one core
    over `dt` seconds, hottest first. A thread new in `after` counts from zero."""
    rows = []
    for tid, (comm, ticks) in after.items():
        prev = before.get(tid, (comm, 0))[1]
        pct = (ticks - prev) / CLK / dt * 100.0
        if pct >= floor:
            rows.append({"tid": tid, "comm": comm, "pct": round(pct, 1)})
    return sorted(rows, key=lambda r: -r["pct"])


def sample(pid, interval, proc="/proc", sleep=time.sleep):
    """One sample: the per-thread CPU over `interval` seconds, and the resident size."""
    before = read_threads(pid, proc)
    t0 = time.monotonic()
    sleep(interval)
    after = read_threads(pid, proc)
    dt = time.monotonic() - t0
    rows = delta(before, after, dt)
    return {
        "t": int(time.time()),
        "pid": pid,
        "rss_kb": rss_kb(pid, proc),
        "total_pct": round(sum(r["pct"] for r in rows), 1),
        "threads": rows[:8],
    }


def report(path):
    """Summarise a recorded run: samples, mean/peak total, and each thread's mean share
    over the samples it appeared in, plus how many of the samples it led."""
    rows = []
    with open(path) as fh:
        for line in fh:
            if line.strip():
                rows.append(json.loads(line))
    if not rows:
        raise SystemExit(
            f"profile_shell: {path} holds 0 samples: the run recorded nothing"
        )
    totals = [r["total_pct"] for r in rows]
    seen = {}
    led = {}
    for r in rows:
        for th in r["threads"]:
            seen.setdefault(th["comm"], []).append(th["pct"])
        if r["threads"]:
            top = r["threads"][0]["comm"]
            led[top] = led.get(top, 0) + 1
    n = len(rows)
    print(
        f"profile_shell: {n} sample(s); total mean {sum(totals) / n:.1f} %, "
        f"peak {max(totals):.1f} %; rss first {rows[0]['rss_kb']} kB, "
        f"last {rows[-1]['rss_kb']} kB, peak {max(r['rss_kb'] for r in rows)} kB "
        f"at sample {max(range(n), key=lambda k: rows[k]['rss_kb']) + 1} of {n}; "
        f"clock {rows[0]['t']} to {rows[-1]['t']}"
    )
    for comm, pcts in sorted(seen.items(), key=lambda kv: -sum(kv[1])):
        print(
            f"  {comm:<18} mean {sum(pcts) / len(pcts):6.1f} % over {len(pcts)} of {n}"
            f" sample(s); led {led.get(comm, 0)}"
        )
    return rows


def holders(top=12, proc="/proc"):
    """[(rss_kb + swap_kb, pid, comm, rss_kb, swap_kb, shmem_kb)] for the `top` processes holding
    the most memory, resident plus swapped (VmRSS, VmSwap, RssShmem). Read per process, so a
    process that exits mid-scan is skipped, never an error. Returns (rows, scanned)."""
    rows = []
    scanned = 0
    for entry in os.listdir(proc):
        if not entry.isdigit():
            continue
        try:
            with open(f"{proc}/{entry}/status") as fh:
                vals = {}
                for line in fh:
                    key, _, rest = line.partition(":")
                    if key in ("Name", "VmRSS", "VmSwap", "RssShmem"):
                        vals[key] = rest.split()[0] if key != "Name" else rest.strip()
        except OSError:
            continue
        scanned += 1
        rss, swap, shm = (int(vals.get(k, 0)) for k in ("VmRSS", "VmSwap", "RssShmem"))
        rows.append((rss + swap, int(entry), vals.get("Name", "?"), rss, swap, shm))
    rows.sort(reverse=True)
    return rows[:top], scanned


def run(pid, interval, out, duration):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    end = None if duration is None else time.monotonic() + duration
    taken = 0
    with open(out, "a") as fh:
        while end is None or time.monotonic() < end:
            try:
                row = sample(pid, interval)
            except (OSError, ProcessLookupError):
                print(f"profile_shell: pid {pid} ended after {taken} sample(s)")
                return taken
            fh.write(json.dumps(row) + "\n")
            fh.flush()
            taken += 1
    print(f"profile_shell: {taken} sample(s) -> {out}")
    return taken


def _selftest():
    import subprocess
    import tempfile

    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    # the parser: a comm with spaces and a ")" inside it
    with tempfile.TemporaryDirectory() as td:
        task = os.path.join(td, "7", "task", "7")
        os.makedirs(task)
        fields = ["S"] + ["0"] * 10 + ["30", "12"] + ["0"] * 10
        with open(os.path.join(task, "stat"), "w") as fh:
            fh.write("7 (Qt (render) x) " + " ".join(fields) + "\n")
        chk(
            "a comm with spaces and parens parses",
            read_threads(7, td),
            {7: ("Qt (render) x", 42)},
        )
    # the delta: a hot thread is reported, a cold one is not, a new one counts from zero
    before = {1: ("main", 0), 2: ("cold", 0)}
    after = {1: ("main", CLK * 5), 2: ("cold", 0), 3: ("new", CLK)}
    chk(
        "a hot thread leads, a cold thread is dropped, a new thread counts from zero",
        [(r["comm"], r["pct"]) for r in delta(before, after, 10.0)],
        [("main", 50.0), ("new", 10.0)],
    )
    # the measurement SEES a real busy child. Judged against the child's OWN CPU time, never a
    # share of a core: a loaded host gives a spinning child any fraction of one (this arm flaked
    # at 'above 50 %' while the gate and a Pod ran, 2026-10-12). The child spins until it has
    # used 1.0 s of CPU, reports that, and waits; the sampler's thread total must agree.
    spin = (
        "import time\nwhile time.process_time() < 1.0: pass\n"
        "print(time.process_time(), flush=True)\ntime.sleep(30)"
    )
    child = subprocess.Popen(
        [sys.executable, "-c", spin], stdout=subprocess.PIPE, text=True
    )
    try:
        own = float((child.stdout.readline() or "nan").split()[0])
        ticks = sum(t for _, t in read_threads(child.pid).values()) / CLK
        chk(
            "the sampled thread CPU matches the child's own process time",
            abs(ticks - own) < 0.3,
            True,
        )
    finally:
        child.kill()
        child.wait()
    # and an idle one reads near zero (the all-clear differs from found-something)
    idle = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    try:
        time.sleep(0.5)
        ticks = sum(t for _, t in read_threads(idle.pid).values()) / CLK
    finally:
        idle.kill()
        idle.wait()
    chk("a sleeping child's CPU seconds stay under 0.3", ticks < 0.3, True)
    print("profile_shell selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    args = argv[1:]
    for a in args:
        if a.startswith("--") and a not in FLAGS:
            print(f"profile_shell: unknown flag '{a}'", file=sys.stderr)
            return 2
    if "--selftest" in args:
        return 0 if _selftest() else 1
    if "--holders" in args:
        rows, scanned = holders()
        if not scanned:
            print(
                "profile_shell: scanned 0 processes: /proc is unreadable",
                file=sys.stderr,
            )
            return 2
        print(
            f"profile_shell: top {len(rows)} of {scanned} process(es) by rss + swap (kB)"
        )
        for tot, pid, name, rss, swap, shm in rows:
            print(
                f"  {pid:>8} {name:<18} total {tot:>10} rss {rss:>10} swap {swap:>10} shmem {shm:>10}"
            )
        return 0
    opts = {}
    for flag in ("--pid", "--interval", "--out", "--duration", "--report"):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                print(f"profile_shell: {flag} needs a value", file=sys.stderr)
                return 2
            opts[flag] = args[i + 1]
    if "--report" in opts:
        report(opts["--report"])
        return 0
    if "--out" not in opts:
        print("profile_shell: --out FILE is required", file=sys.stderr)
        return 2
    pid = int(opts["--pid"]) if "--pid" in opts else find_pid()
    if pid is None:
        print("profile_shell: no plasmashell process found", file=sys.stderr)
        return 2
    dur = float(opts["--duration"]) if "--duration" in opts else None
    run(pid, float(opts.get("--interval", 5)), opts["--out"], dur)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
