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
FLAGS = {"--seconds", "--every", "--mix", "--set", "--env", "--patch", "--selftest"}
# the inputs a soak can switch on, one at a time, to BISECT a cost (the baseline is one normal
# item per burst with a short body): the urgencies, a replace of a visible item, a same-turn
# flash, a job gauge, actions, and the long marked-up body
MIXES = ("low", "critical", "replace", "flash", "job", "actions", "long")
# "idle" is not an input but its absence: a board with NO events at all (the cost of the board
# itself, apart from any notification)
KNOWN = (*MIXES, "idle")


APPS = ("mail", "chat", "build", "calendar", "backup")
BODY = (
    "<b>bold</b> and <i>italic</i> with <u>underline</u>, a "
    "<a href='https://example.test/x'>link</a> and some longer plain text to widen the ticker"
)
LIVE_CYCLES = (
    3  # a cycle's items stay up this many periods, so the ticker holds a dozen or more
)


def soak_timeline(seconds, period_ms=1500, mix=MIXES):
    """A PUMMELLING, switchable by `mix` so a cost can be BISECTED. Every period, a burst of
    notifications: a normal item always, plus (when in `mix`) a low and a CRITICAL one (which
    blinks), a long marked-up body (else a short one), actions, a flash that arrives and vanishes
    in one turn, a replace of a visible item, and a job gauge. Each item stays up LIVE_CYCLES
    periods, so the ring holds a dozen or more (the live board's ticker held about 228
    characters, a 6004 px backdrop; the full mix holds several times that)."""
    if "idle" in mix:
        return []
    out = []
    nid = 0
    body = BODY if "long" in mix else "short"
    urgencies = [1] + [u for u, name in ((0, "low"), (2, "critical")) if name in mix]
    for k in range(max(1, int(seconds * 1000 // period_ms))):
        t = 700 + k * period_ms
        ids = []
        for j, urgency in enumerate(urgencies):
            nid += 1
            ids.append(nid)
            fields = {
                "summary": f"item {nid}",
                "body": body,
                "applicationName": APPS[(k + j) % len(APPS)],
                "urgency": urgency,
            }
            if "actions" in mix and j == 0:
                fields["actionNames"] = ["open", "later"]
                fields["actionLabels"] = ["Open", "Later"]
            out.append((t + 100 * j, "arrive", nid, fields, ""))
        if "flash" in mix:
            nid += 1
            fl = {"summary": "flash", "applicationName": "app"}
            out.append((t + 450, "flash", nid, fl, ""))
        if "replace" in mix:
            fields = {
                "summary": f"item {ids[0]}",
                "body": "changed " + body,
                "applicationName": "app",
            }
            out.append((t + 600, "replace", ids[0], fields, ""))
        if "job" in mix:
            nid += 1
            ids.append(nid)
            job = {"type": 2, "jobState": 1, "percentage": (k * 7) % 100}
            fields = {"summary": "job", "applicationName": "app", **job}
            out.append((t + 700, "arrive", nid, fields, ""))
        for i in ids:
            out.append((t + LIVE_CYCLES * period_ms + 900, "expire", i, {}, ""))
    return sorted(out, key=lambda e: e[0])


def apply_patch(directory, spec):
    """Rewrite one staged file: spec is 'FILE:OLD=>NEW'. OLD must occur (a patch that matches
    nothing is refused, never a silent no-op). For EXPERIMENTS on the staged copy only: the
    repository's templates are never touched."""
    name, _, rule = spec.partition(":")
    old, sep, new = rule.partition("=>")
    path = os.path.join(directory, name)
    if not sep or not old or not os.path.isfile(path):
        raise SystemExit(
            f"marquee_soak: bad patch {spec!r} (FILE:OLD=>NEW, file staged)"
        )
    with open(path) as fh:
        text = fh.read()
    if old not in text:
        raise SystemExit(f"marquee_soak: patch {spec!r}: {old!r} not found in {name}")
    with open(path, "w") as fh:
        fh.write(text.replace(old, new))


def stage(directory, seconds, mix=MIXES, config=None, extra_env=None, patches=()):
    """Write the run into `directory` and return its soak.json (argv and env hold {DIR})."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)
    os.chdir(root)
    import check_marquee_live as CM

    os.makedirs(directory, exist_ok=True)
    stager = CM.stager(
        end_ms=int(seconds * 1000),
        timeline=soak_timeline(seconds, mix=mix),
        config_overrides=config,
    )
    argv, env, _rhi = stager(directory)
    for patch in patches:
        apply_patch(directory, patch)

    def sub(text):
        return text.replace(directory, "{DIR}")

    spec = {
        "argv": [sub(a) for a in argv],
        "env": {
            k: sub(v) for k, v in env.items() if any(k.startswith(p) for p in KEEP)
        },
        "seconds": seconds,
        "mix": list(mix),
        "config": config or {},
    }
    spec["env"].update(extra_env or {})
    with open(os.path.join(directory, "soak.json"), "w") as fh:
        json.dump(spec, fh, indent=1)
    return spec


def parse_set(text):
    """{key: value} from 'key=value,key=value'; each value is read as JSON (false, 1.5, "x"),
    else kept as the string."""
    out = {}
    for pair in filter(None, text.split(",")):
        key, _, raw = pair.partition("=")
        try:
            out[key] = json.loads(raw)
        except ValueError:
            out[key] = raw
    return out


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
    out = {**summarise(rows, proc.returncode), "exercised": log_facts(log_path)}
    swaps = out["exercised"]["swaps"]
    if swaps and "cpu_s" in out:
        out["cpu_ms_per_swap"] = round(1000 * out["cpu_s"] / swaps, 2)
    return out


def log_facts(path):
    """What the run's own output says it did: lines, el-marquee trace lines, whether RESULT
    printed. A flat memory trace means nothing if the board never ran (a silent harness)."""
    with open(path, errors="replace") as fh:
        return log_facts_of(fh.read().splitlines())


def log_facts_of(lines):
    """log_facts over lines already read."""
    kinds = {}
    for line in lines:
        head = line.split(" ", 1)[0].rstrip(":")[:40]
        kinds[head] = kinds.get(head, 0) + 1
    swaps = None
    for line in lines:
        if line.startswith("RESULT ") or " RESULT " in line:
            try:
                swaps = json.loads(line.split("RESULT ", 1)[1]).get("swaps")
            except ValueError:
                swaps = None
    return {
        "lines": len(lines),
        "trace": sum("el-marquee " in line for line in lines),
        "result": any("RESULT " in line for line in lines),
        "swaps": swaps,
        "kinds": dict(sorted(kinds.items(), key=lambda kv: -kv[1])[:6]),
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
    # the mix switches each input on and off: the baseline is normal items only, and each input
    # added shows up in the timeline and only then
    base = soak_timeline(10, 1500, mix=())
    chk(
        "the empty mix is normal arrivals and expires only",
        {e[1] for e in base} | {e[3].get("urgency") for e in base if e[1] == "arrive"},
        {"arrive", "expire", 1},
    )
    for name, op in (("flash", "flash"), ("replace", "replace")):
        chk(
            f"mix {name} adds the {op} op and nothing else adds it",
            (
                op in {e[1] for e in soak_timeline(10, 1500, mix=(name,))},
                op in {e[1] for e in base},
            ),
            (True, False),
        )
    crit = soak_timeline(10, 1500, mix=("critical",))
    chk(
        "mix critical adds urgency 2 and not urgency 0",
        {e[3].get("urgency") for e in crit if e[1] == "arrive"},
        {1, 2},
    )
    chk("the idle mix has no events at all", soak_timeline(10, 1500, mix=("idle",)), [])
    with tempfile.TemporaryDirectory() as td:
        with open(os.path.join(td, "f.qml"), "w") as fh:
            fh.write("a: integrate()\n")
        apply_patch(td, "f.qml:integrate()=>0")
        with open(os.path.join(td, "f.qml")) as fh:
            chk("a patch rewrites the staged file", fh.read(), "a: 0\n")
        refused = []
        for bad in ("f.qml:absent=>x", "f.qml:noarrow", "nofile.qml:a=>b"):
            try:
                apply_patch(td, bad)
                refused.append(False)
            except SystemExit:
                refused.append(True)
        chk(
            "a patch that matches nothing or is malformed is refused",
            refused,
            [True] * 3,
        )
    chk(
        "the frames swapped are read from the RESULT line, None when absent",
        (
            log_facts_of(['RESULT {"swaps": 120}'])["swaps"],
            log_facts_of(["RESULT {}"])["swaps"],
        ),
        (120, None),
    )
    kinds = log_facts_of(["a: 1", "a: 2", "b x", "RESULT {}"])["kinds"]
    chk(
        "the log's line kinds are tallied, commonest first",
        list(kinds.items())[:2],
        [("a", 2), ("b", 1)],
    )
    with tempfile.TemporaryDirectory() as td:
        env_spec = stage(os.path.join(td, "e"), 6, ("idle",), None, {"QT_X": "1"})
        chk(
            "an extra env name rides in the staged spec",
            env_spec["env"].get("QT_X"),
            "1",
        )
    chk(
        "--set reads JSON values and keeps strings",
        parse_set("showField=false,pitchScale=1.5,name=x"),
        {"showField": False, "pitchScale": 1.5, "name": "x"},
    )
    with tempfile.TemporaryDirectory() as td:
        idle_spec = stage(os.path.join(td, "i"), 6, ("idle",), {"showField": False})
        with open(os.path.join(td, "i", "harness.qml")) as fh:
            harness = fh.read()
        chk(
            "an idle staged run carries the override in its harness and no events",
            ('"showField": false' in harness, idle_spec["config"]),
            (True, {"showField": False}),
        )
    chk(
        "mix long widens the body",
        len(soak_timeline(10, 1500, mix=("long",))[0][3]["body"])
        > len(base[0][3]["body"]),
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
    patches = []
    while "--patch" in args:
        i = args.index("--patch")
        if i + 1 >= len(args):
            print("marquee_soak: --patch needs a value", file=sys.stderr)
            return 2
        patches.append(args.pop(i + 1))
        args.pop(i)
    for flag in ("--seconds", "--every", "--mix", "--set", "--env"):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                print(f"marquee_soak: {flag} needs a value", file=sys.stderr)
                return 2
            raw = args.pop(i + 1)
            opts[flag] = float(raw) if flag in ("--seconds", "--every") else raw
            args.pop(i)
    if len(args) != 2 or args[0] not in ("stage", "run"):
        print(
            "usage: marquee_soak.py stage|run DIR [--seconds N] [--every S] "
            "[--mix a,b|none] [--set key=value,key=value]",
            file=sys.stderr,
        )
        return 2
    mix = MIXES
    if "--mix" in opts:
        mix = tuple(m for m in opts["--mix"].split(",") if m and m != "none")
        unknown = [m for m in mix if m not in KNOWN]
        if unknown:
            print(
                f"marquee_soak: unknown mix {unknown}; known {KNOWN}", file=sys.stderr
            )
            return 2
    config = parse_set(opts.get("--set", ""))
    key, _, value = opts.get("--env", "").partition("=")
    extra_env = {key: value} if key else {}
    if key and not any(key.startswith(p) for p in KEEP):
        print(f"marquee_soak: --env {key} is outside {KEEP}", file=sys.stderr)
        return 2
    directory = os.path.abspath(args[1])
    seconds = opts.get("--seconds", 120.0)
    if args[0] == "stage":
        stage(directory, seconds, mix, config, extra_env, patches)
        print(
            f"marquee_soak: staged {seconds:.0f} s, mix {list(mix)}, "
            f"set {config}, into {directory}"
        )
        return 0
    summary = run(directory, opts.get("--seconds"), opts.get("--every", 2.0))
    return 0 if summary["samples"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
