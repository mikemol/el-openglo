#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""marquee_soak.py — a long marquee run whose memory is sampled, for a MEMORY-LIMITED host.

⚑ WHY (operator, 2026-10-12: the marquee widget ate all RAM then all swap on the live desktop;
luthen's series shows Shmem 13.5 -> 19.7 GB in 15 min, luthen-observability:W838). The harness
(check_marquee_live) runs the board for seconds; a leak needs minutes of arrive/expire cycles
and a sampler. This is TWO halves so the memory-limited half carries no repository:

    scripts/marquee_soak.py stage DIR [--seconds N]   # HOST: write the harness, the QML and
                                                      # soak.json (argv, env with {DIR})
    scripts/marquee_soak.py run DIR [--seconds N] [--every S]
                                                      # ANYWHERE with qml: stdlib only; runs
                                                      # soak.json, samples rss / RssShmem
    scripts/marquee_soak.py --selftest

`stage` needs this repository (it reuses check_marquee_live's stager, so the soak runs the SAME
subject and harness the gates do); `run` needs only Python and a `qml` binary, so a Pod holding
nothing but the staged directory can do it. `run` writes DIR/samples.jsonl and DIR/summary.json.

WEAKNESS: the offscreen software scene graph. A leak in the QML/JS, the Canvas or the JS heap
shows here; Shmem growth through a real Wayland client (wl_shm buffers into a compositor) does
NOT, because there is no compositor. A clean soak therefore does not clear the widget, it
clears the QML. The staged env keeps only QT/QML/QSG/KDE names, so the host's theme file is not
carried: the board draws under Kirigami's default theme in the Pod.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

KEEP = ("QT_", "QML", "QSG_", "KDE_")
FLAGS = {"--seconds", "--every", "--selftest"}


APPS = ("mail", "chat", "build", "calendar", "backup")
BODY = (
    "<b>bold</b> and <i>italic</i> with <u>underline</u>, a "
    "<a href='https://example.test/x'>link</a> and some longer plain text to widen the ticker"
)
LIVE_CYCLES = (
    3  # a cycle's items stay up this many periods, so the ticker holds a dozen or more
)


def soak_timeline(seconds, period_ms=1500):
    """A PUMMELLING: every period, a burst of notifications of every urgency (low, normal and
    CRITICAL, which blinks) with long marked-up bodies and actions, a flash that arrives and
    vanishes in one turn, a replace of a visible item, and a job gauge; each item stays up
    LIVE_CYCLES periods, so the ring holds a dozen or more items (the live board's ticker held
    about 228 characters, a 6004 px backdrop; this holds several times that)."""
    out = []
    nid = 0
    for k in range(max(1, int(seconds * 1000 // period_ms))):
        t = 700 + k * period_ms
        ids = []
        for j, urgency in enumerate((1, 0, 2, 1)):
            nid += 1
            ids.append(nid)
            fields = {
                "summary": f"item {nid}",
                "body": BODY,
                "applicationName": APPS[(k + j) % len(APPS)],
                "urgency": urgency,
            }
            if j == 3:
                fields["actionNames"] = ["open", "later"]
                fields["actionLabels"] = ["Open", "Later"]
            out.append((t + 100 * j, "arrive", nid, fields, ""))
        nid += 1
        out.append(
            (t + 450, "flash", nid, {"summary": "flash", "applicationName": "app"}, "")
        )
        out.append(
            (
                t + 600,
                "replace",
                ids[0],
                {
                    "summary": f"item {ids[0]}",
                    "body": "changed " + BODY,
                    "applicationName": "app",
                },
                "",
            )
        )
        nid += 1
        job = {"type": 2, "jobState": 1, "percentage": (k * 7) % 100}
        out.append(
            (
                t + 700,
                "arrive",
                nid,
                {"summary": "job", "applicationName": "app", **job},
                "",
            )
        )
        for i in ids + [nid]:
            out.append((t + LIVE_CYCLES * period_ms + 900, "expire", i, {}, ""))
    return sorted(out, key=lambda e: e[0])


def stage(directory, seconds):
    """Write the run into `directory` and return its soak.json (argv and env hold {DIR})."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)
    os.chdir(root)
    import check_marquee_live as CM

    os.makedirs(directory, exist_ok=True)
    stager = CM.stager(end_ms=int(seconds * 1000), timeline=soak_timeline(seconds))
    argv, env, _rhi = stager(directory)

    def sub(text):
        return text.replace(directory, "{DIR}")

    spec = {
        "argv": [sub(a) for a in argv],
        "env": {
            k: sub(v) for k, v in env.items() if any(k.startswith(p) for p in KEEP)
        },
        "seconds": seconds,
    }
    with open(os.path.join(directory, "soak.json"), "w") as fh:
        json.dump(spec, fh, indent=1)
    return spec


def read_status(pid):
    """{VmRSS, RssShmem, RssAnon} in kB for `pid`, or None once it has gone."""
    try:
        with open(f"/proc/{pid}/status") as fh:
            return {
                k: int(v.split()[0])
                for k, _, v in (line.partition(":") for line in fh)
                if k in ("VmRSS", "RssShmem", "RssAnon")
            }
    except OSError:
        return None


def read_cpu(pid):
    """The process's CPU seconds so far (utime + stime), or None once it has gone."""
    try:
        with open(f"/proc/{pid}/stat") as fh:
            fields = fh.read().rpartition(")")[2].split()
    except OSError:
        return None
    return (int(fields[11]) + int(fields[12])) / os.sysconf("SC_CLK_TCK")


def sample_run(argv, env, seconds, every, out_dir):
    """Run `argv` for at most `seconds` (+ grace), sampling its memory every `every` seconds."""
    log_path = os.path.join(out_dir, "qml.log")
    rows = []
    t0 = time.monotonic()
    with open(log_path, "w") as log:
        proc = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            while proc.poll() is None and time.monotonic() - t0 < seconds + 30:
                st = read_status(proc.pid)
                if st is not None:
                    row = {"t": round(time.monotonic() - t0, 1), **st}
                    cpu = read_cpu(proc.pid)
                    if cpu is not None:
                        row["cpu_s"] = round(cpu, 2)
                    rows.append(row)
                time.sleep(every)
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
    with open(os.path.join(out_dir, "samples.jsonl"), "w") as fh:
        fh.writelines(json.dumps(r) + "\n" for r in rows)
    return {**summarise(rows, proc.returncode), "exercised": log_facts(log_path)}


def log_facts(path):
    """What the run's own output says it did: lines, el-marquee trace lines, whether RESULT
    printed. A flat memory trace means nothing if the board never ran (a silent harness)."""
    with open(path, errors="replace") as fh:
        lines = fh.read().splitlines()
    return {
        "lines": len(lines),
        "trace": sum("el-marquee " in line for line in lines),
        "result": any("RESULT " in line for line in lines),
    }


def summarise(rows, rc):
    """Facts only: n of m samples, first/last/peak of rss and Shmem, the child's exit code."""
    if not rows:
        return {
            "samples": 0,
            "rc": rc,
            "verdict": "no samples: the run recorded nothing",
        }
    out = {"samples": len(rows), "rc": rc, "span_s": rows[-1]["t"]}
    timed = [r for r in rows if "cpu_s" in r]
    if len(timed) > 1 and timed[-1]["t"] > timed[0]["t"]:
        used = timed[-1]["cpu_s"] - timed[0]["cpu_s"]
        out["cpu_pct_mean"] = round(100 * used / (timed[-1]["t"] - timed[0]["t"]), 1)
        out["cpu_s"] = timed[-1]["cpu_s"]
    for key in ("VmRSS", "RssShmem", "RssAnon"):
        vals = [r[key] for r in rows if key in r]
        if vals:
            out[key] = {"first": vals[0], "last": vals[-1], "peak": max(vals)}
    return out


def resolve_binary(path, exists=os.path.exists, which=shutil.which):
    """`path` when it exists here, else the same binary found by name or under the Debian Qt 6
    directory: the host staged /usr/lib64/qt6/bin/qml (Gentoo), a Debian-family image has
    /usr/lib/qt6/bin/qml. A binary found nowhere is returned unchanged, so the failure names it."""
    if exists(path):
        return path
    name = os.path.basename(path)
    for found in (which(name), os.path.join("/usr/lib/qt6/bin", name)):
        if found and exists(found):
            return found
    return path


def run(directory, seconds, every):
    with open(os.path.join(directory, "soak.json")) as fh:
        spec = json.load(fh)
    seconds = seconds or spec["seconds"]
    argv = [a.replace("{DIR}", directory) for a in spec["argv"]]
    argv[0] = resolve_binary(argv[0])
    env = dict(os.environ)
    env.update({k: v.replace("{DIR}", directory) for k, v in spec["env"].items()})
    summary = sample_run(argv, env, seconds, every, directory)
    with open(os.path.join(directory, "summary.json"), "w") as fh:
        json.dump(summary, fh, indent=1)
    print(json.dumps(summary))
    return summary


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    tl = soak_timeline(10, 1500)
    arrived = {e[2]: e[0] for e in tl if e[1] in ("arrive", "flash")}
    expired = {e[2]: e[0] for e in tl if e[1] == "expire"}
    ops = {e[1] for e in tl}
    urgencies = {e[3].get("urgency") for e in tl if e[1] == "arrive"}
    chk(
        "the timeline is time-ordered",
        [e[0] for e in tl] == sorted(e[0] for e in tl),
        True,
    )
    chk(
        "it pummels: arrive, flash, replace and expire all occur",
        ops >= {"arrive", "flash", "replace", "expire"},
        True,
    )
    chk(
        "every urgency appears, critical included (the blinking one)",
        {0, 1, 2} <= urgencies,
        True,
    )
    chk(
        "every expired item had arrived first",
        all(arrived[i] < expired[i] for i in expired),
        True,
    )
    chk(
        "items overlap, so the ring holds many at once",
        max(
            sum(1 for i in expired if arrived[i] <= t < expired[i])
            for t in sorted(arrived.values())
        )
        >= 12,
        True,
    )
    # the sampler SEES growth: a child that holds more memory each step shows a rising peak
    # (the bytes are TOUCHED: a zero-filled bytearray is never made resident, which would make
    # this arm see nothing whether or not the sampler works)
    grow = (
        "import time\nb = []\n"
        "for _ in range(40):\n"
        "    b.append(b'\\x01' * (2 * 1024 * 1024))\n"
        "    time.sleep(0.05)\n"
        "time.sleep(1)\n"
    )
    flat = "import time\nx = b'\\x01' * (8 * 1024 * 1024)\ntime.sleep(2)\n"
    with tempfile.TemporaryDirectory() as td:
        g = sample_run([sys.executable, "-c", grow], dict(os.environ), 20, 0.2, td)
        chk(
            "a child growing 80 MB shows its peak 50 MB above its first",
            g["VmRSS"]["peak"] > g["VmRSS"]["first"] + 50000,
            True,
        )
        # ...and a flat child does not (the all-clear differs from found-something)
        f = sample_run([sys.executable, "-c", flat], dict(os.environ), 20, 0.2, td)
        chk(
            "a flat 8 MB child's peak stays within 20 MB of its first",
            f["VmRSS"]["peak"] < f["VmRSS"]["first"] + 20000,
            True,
        )
    # CPU is judged against the CHILD'S OWN CPU time, never a share of a core: a loaded host
    # gives a spinning child any fraction of a core (a flake measured 2026-10-12 under the gate)
    spin = (
        "import time\nwhile time.process_time() < 1.5: pass\n"
        "print(time.process_time())\ntime.sleep(1)\n"
    )
    nap = "import time\ntime.sleep(3)\n"
    with tempfile.TemporaryDirectory() as td:
        hot = sample_run([sys.executable, "-c", spin], dict(os.environ), 60, 0.3, td)
        with open(os.path.join(td, "qml.log")) as fh:
            own = float(fh.read().split()[0])
        chk(
            "the sampled CPU seconds match the child's own process time",
            abs(hot["cpu_s"] - own) < 0.6,
            True,
        )
        cold = sample_run([sys.executable, "-c", nap], dict(os.environ), 60, 0.3, td)
        chk("a sleeping child's CPU seconds stay under 0.5", cold["cpu_s"] < 0.5, True)
    talk = "print('el-marquee paint idle=false');print('RESULT {}')"
    with tempfile.TemporaryDirectory() as td:
        t = sample_run([sys.executable, "-c", talk], dict(os.environ), 5, 0.1, td)
        chk(
            "the run's own output is read back: one trace line and a RESULT",
            (t["exercised"]["trace"], t["exercised"]["result"]),
            (1, True),
        )
        q = sample_run([sys.executable, "-c", "pass"], dict(os.environ), 5, 0.1, td)
        chk(
            "a silent child reports no trace and no RESULT",
            (q["exercised"]["trace"], q["exercised"]["result"]),
            (0, False),
        )
    present = {"/usr/lib/qt6/bin/qml"}
    chk(
        "a Gentoo qml path resolves to the Debian one when only that exists",
        resolve_binary(
            "/usr/lib64/qt6/bin/qml",
            exists=present.__contains__,
            which=lambda n: None,
        ),
        "/usr/lib/qt6/bin/qml",
    )
    chk(
        "a binary found nowhere is returned unchanged so the failure names it",
        resolve_binary("/nope/qml", exists=lambda p: False, which=lambda n: None),
        "/nope/qml",
    )
    chk(
        "an empty run is reported, never a clean zero",
        "no samples" in summarise([], 0)["verdict"],
        True,
    )
    # the staged directory carries no host path and the keep-list holds
    with tempfile.TemporaryDirectory() as td:
        spec = stage(os.path.join(td, "s"), 6)
        names = ("soak.json", "subject.qml", "harness.qml")
        chk("the staged spec names no host directory", td in json.dumps(spec), False)
        chk(
            "the staged files exist",
            all(os.path.isfile(os.path.join(td, "s", n)) for n in names),
            True,
        )
        chk(
            "the staged env keeps only QT/QML/QSG/KDE names",
            all(any(k.startswith(p) for p in KEEP) for k in spec["env"]),
            True,
        )
    print("marquee_soak selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    args = argv[1:]
    for a in args:
        if a.startswith("--") and a not in FLAGS:
            print(f"marquee_soak: unknown flag '{a}'", file=sys.stderr)
            return 2
    if "--selftest" in args:
        return 0 if _selftest() else 1
    opts = {}
    for flag in ("--seconds", "--every"):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                print(f"marquee_soak: {flag} needs a value", file=sys.stderr)
                return 2
            opts[flag] = float(args.pop(i + 1))
            args.pop(i)
    if len(args) != 2 or args[0] not in ("stage", "run"):
        print(
            "usage: marquee_soak.py stage|run DIR [--seconds N] [--every S]",
            file=sys.stderr,
        )
        return 2
    directory = os.path.abspath(args[1])
    seconds = opts.get("--seconds", 120.0)
    if args[0] == "stage":
        stage(directory, seconds)
        print(f"marquee_soak: staged {seconds:.0f} s into {directory}")
        return 0
    summary = run(directory, opts.get("--seconds"), opts.get("--every", 2.0))
    return 0 if summary["samples"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
