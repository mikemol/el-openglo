#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""el_serial_emit.py — the pure-Python REFERENCE writer of el-serial/1.

The guest runs guest/el-serial-emit.sh (POSIX sh + jq; there is no Python in the
guest). This file implements the same spec, catalog/guest-image.md (f), on the
host, so the round trip (emit a boot, read it back with read_serial.py) can be
proved here, and so the fixtures under catalog/fixtures/serial/ are generated,
not hand-typed. Both writers take every kind, payload key and type from
guest/el-serial-spec.json (through el_serial_spec here, through jq there).

    scripts/el_serial_emit.py --fixtures DIR   # write the four fixtures into DIR
    scripts/el_serial_emit.py --selftest       # round trip + committed fixtures == regenerated

    scripts/el_serial_emit.py --sh-bundle DIR  # a build context: run.sh drives the sh writer and cmp's it

The sh writer is compared BYTE FOR BYTE with this one (W232): `--sh-bundle` writes
the P2 boot as operations (one sh invocation each, the clock set per operation),
the reference log, and a run.sh that replays them through guest/el-serial-emit.sh
and cmp's. The selftest runs it where jq and flock exist and SKIPs (counted)
where not; luthen-observability's checks.serial_writer runs it in a debian image.
Its first run (2026-10-02) found two real defects in the sh writer.

Weakness: the comparison covers the P2 operation sequence only, in debian-slim's
jq/coreutils, not the guest image's own; the first guest boot (W71e) is still
where the guest's bytes meet the reader.
"""

import base64
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import el_serial_spec

ROOT = el_serial_spec.ROOT
FIXTURES = os.path.join(ROOT, "catalog", "fixtures", "serial")


class Emitter:
    """One boot's writer. `clock()` returns centiseconds since boot (int)."""

    def __init__(self, boot, clock, spec=None):
        self.spec = spec or el_serial_spec.load()
        self.boot, self.clock, self.seq, self.lines = boot, clock, 0, []

    def frame(self, kind, **payload):
        if set(payload) & set(self.spec["envelope"]):
            raise ValueError(
                f"{kind}: payload must not carry the envelope keys {sorted(self.spec['envelope'])}"
            )
        obj = dict(payload, boot=self.boot, t=self.clock())
        errs = el_serial_spec.validate(self.spec, kind, obj)
        if errs:
            raise ValueError("; ".join(errs))
        line = (
            f"{self.spec['marker']} {self.seq} {kind} {el_serial_spec.canonical(obj)}"
        )
        if len(line.encode()) > self.spec["max_line_bytes"]:
            raise ValueError(
                f"{kind}: {len(line.encode())} bytes > {self.spec['max_line_bytes']}; send it as a blob"
            )
        self.seq += 1
        self.lines.append(line)
        return line

    def blob(self, label, data):
        """blob.part 0..of-1 then blob.end, consecutive (one lock hold). Returns the id."""
        bid = f"b{self.seq}"
        b64 = base64.b64encode(data).decode()
        w = self.spec["part_b64_chars"]
        parts = [b64[i : i + w] for i in range(0, len(b64), w)] or [""]
        for n, chunk in enumerate(parts):
            self.frame("blob.part", id=bid, n=n, of=len(parts), b64=chunk)
        self.frame(
            "blob.end",
            id=bid,
            sha256=hashlib.sha256(data).hexdigest(),
            bytes=len(data),
            of=len(parts),
            label=label,
        )
        return bid

    def done(self, probe):
        return self.frame("el.done", probe=probe, records=self.seq)


def _ticker(start=150, step=37):
    t = [start]

    def clock():
        t[0] += step
        return t[0]

    return clock


BOOT = "3f1c2b9e-8a4d-4e6f-9b1a-0c2d4e6f8a1b"
NOISE = [
    "[    0.000000] Linux version 6.12.48+deb13-amd64 (debian-kernel@lists.debian.org)",
    "[    1.204411] systemd[1]: Detected virtualization kvm.",
    "[  OK  ] Started systemd-journald.service - Journal Service.",
    "Debian GNU/Linux 13 el-probe ttyS0",
    "[   14.880102] zram0: detected capacity change from 0 to 1409024",
    "el-probe login: ",
]


def p2_boot():
    """A complete P2 (wallpaper) boot: every kind P2 requires, three journals, one file."""
    e = Emitter(BOOT, _ticker())
    e.frame(
        "el.ident",
        guest={
            "deb_sha256": "0" * 64,
            "git_rev": "4abcb5b",
            "snapshot": "20260920T000000Z",
        },
        cmdline="BOOT_IMAGE=/vmlinuz quiet splash console=tty0 console=ttyS0 el.probe=P2",
        probe="P2",
    )
    mem = {
        "mem_total_kb": 716800,
        "mem_available_kb": 402112,
        "swap_total_kb": 358400,
        "swap_free_kb": 358400,
        "zram_orig_bytes": 0,
        "zram_compr_bytes": 0,
    }
    e.frame("el.mem", **mem)
    e.frame("el.session", uid=1000, session_type="wayland")
    e.frame("el.settled", capped=False)
    j = {
        name: e.blob(
            f"journal.{name}",
            ("\n".join(f'{{"MESSAGE":"{name} line {i}"}}' for i in range(40))).encode(),
        )
        for name in ("sddm", "plasmashell", "plymouth")
    }
    e.frame("el.journal", **j)
    f = e.blob(
        "appletsrc",
        b"[Containments][1][Wallpaper][org.kde.image][General]\nImage=EL-Openglo\n"
        * 20,
    )
    e.frame("el.file", appletsrc=f)
    e.frame("el.mem", **dict(mem, mem_available_kb=198656))
    e.done("P2")
    return e.lines


def p2_ops():
    """The P2 boot as OPERATIONS, the unit both writers share: ("frame", kind, payload),
    ("blob", label, bytes), ("done", probe). One op is one sh-writer invocation."""
    mem = {
        "mem_total_kb": 716800,
        "mem_available_kb": 402112,
        "swap_total_kb": 358400,
        "swap_free_kb": 358400,
        "zram_orig_bytes": 0,
        "zram_compr_bytes": 0,
    }
    ops = [
        (
            "frame",
            "el.ident",
            {
                "guest": {
                    "deb_sha256": "0" * 64,
                    "git_rev": "4abcb5b",
                    "snapshot": "20260920T000000Z",
                },
                "cmdline": "BOOT_IMAGE=/vmlinuz quiet splash console=tty0 console=ttyS0 el.probe=P2",
                "probe": "P2",
            },
        ),
        ("frame", "el.mem", mem),
        ("frame", "el.session", {"uid": 1000, "session_type": "wayland"}),
        ("frame", "el.settled", {"capped": False}),
    ]
    # a blob id is "b<seq of its first part>", deterministic; a scratch writer finds them
    scratch = Emitter(BOOT, lambda: 0)
    for op in ops:
        scratch.frame(op[1], **op[2])
    j = {}
    for name in ("sddm", "plasmashell", "plymouth"):
        data = (
            "\n".join(f'{{"MESSAGE":"{name} line {i}"}}' for i in range(40))
        ).encode()
        ops.append(("blob", f"journal.{name}", data))
        j[name] = scratch.blob(f"journal.{name}", data)
    ops.append(("frame", "el.journal", j))
    scratch.frame("el.journal", **j)
    data = (
        b"[Containments][1][Wallpaper][org.kde.image][General]\nImage=EL-Openglo\n" * 20
    )
    ops += [
        ("blob", "appletsrc", data),
        ("frame", "el.file", {"appletsrc": scratch.blob("appletsrc", data)}),
        ("frame", "el.mem", dict(mem, mem_available_kb=198656)),
        ("done", "P2"),
    ]
    return ops


def op_reference(ops, start=150, step=37):
    """(lines, [t per op]): the reference writer over `ops` with the clock set ONCE per
    op - the sh writer's granularity, since it reads the clock per invocation and a
    blob is one invocation. Blob ids feed the el.journal / el.file frames as P2 does."""
    t = [start]
    e = Emitter(BOOT, lambda: t[0])
    times = []
    for op in ops:
        t[0] += step
        times.append(t[0])
        if op[0] == "frame":
            e.frame(op[1], **op[2])
        elif op[0] == "blob":
            e.blob(op[1], op[2])
        else:
            e.done(op[1])
    return e.lines, times


def sh_bundle(d, ops=None):
    """Write a build context in which `sh run.sh` drives guest/el-serial-emit.sh through
    `ops` and byte-compares its log with the reference writer's (exit 0 equal, 1 not).
    Needs sh + jq + coreutils + flock: luthen-observability's checks.serial_writer runs it."""
    import json
    import shutil

    ops = ops or p2_ops()
    lines, times = op_reference(ops)
    os.makedirs(os.path.join(d, "blobs"), exist_ok=True)
    shutil.copy(
        os.path.join(ROOT, "guest", "el-serial-emit.sh"),
        os.path.join(d, "el-serial-emit.sh"),
    )
    shutil.copy(el_serial_spec.SPEC_PATH, os.path.join(d, "el-serial-spec.json"))
    with open(os.path.join(d, "expected.log"), "w") as f:
        f.write("".join(x + "\n" for x in lines))
    with open(os.path.join(d, "boot_id"), "w") as f:
        f.write(BOOT + "\n")
    q = lambda s: "'" + s.replace("'", "'\\''") + "'"
    sh = [
        "#!/bin/sh",
        "# GENERATED by scripts/el_serial_emit.py --sh-bundle (W232); do not hand-edit.",
        "set -eu",
        'cd "$(dirname "$0")"',
        "W=$(mktemp -d)",
        'export EL_SERIAL_SPEC=el-serial-spec.json EL_SERIAL_DEV="$W/log" EL_SERIAL_RUN="$W"',
        'export EL_SERIAL_BOOT_FILE=boot_id EL_SERIAL_UPTIME_FILE="$W/uptime"',
        ': > "$W/log"',
    ]
    for i, (op, t) in enumerate(zip(ops, times)):
        sh.append(f'echo "{t // 100}.{t % 100:02d} 0.00" > "$W/uptime"')
        if op[0] == "frame":
            sh.append(
                f"sh el-serial-emit.sh frame {op[1]} {q(json.dumps(op[2], sort_keys=True))}"
            )
        elif op[0] == "blob":
            with open(os.path.join(d, "blobs", f"{i}.bin"), "wb") as f:
                f.write(op[2])
            sh.append(f"sh el-serial-emit.sh blob {q(op[1])} blobs/{i}.bin > /dev/null")
        else:
            sh.append(f"sh el-serial-emit.sh done {q(op[1])}")
    sh += [
        'if cmp -s "$W/log" expected.log; then echo "sh writer == reference: $(wc -l < expected.log) lines"; exit 0; fi',
        'echo "sh writer != reference" >&2',
        'diff "$W/log" expected.log >&2 || true',
        "exit 1",
    ]
    with open(os.path.join(d, "run.sh"), "w") as f:
        f.write("\n".join(sh) + "\n")
    return len(lines)


STUB_TOOLS = {
    # the guest tools the reporter calls, as stubs that succeed with fixed output
    "journalctl": 'echo "{\\"MESSAGE\\":\\"stub journal $*\\"}"',
    "systemctl": "exit 0",
    "systemd-analyze": 'echo "stub systemd-analyze $*"',
    "pgrep": 'case "$*" in *plasmashell*|*sddm-greeter-qt6*) echo 4242 ;; *) exit 1 ;; esac',
    "sleep": "exit 0",
    "id": "echo 1000",
}


def reporter_bundle(d, probes=("P1", "P2", "P3", "P4", "P4g")):
    """Write a build context whose run.sh drives guest/el-reporter.sh through one boot
    per probe on stub files and stub guest tools, and prints the serial log on stdout
    (one boot per probe, boot ids distinct). The host then judges that log with
    `opa_gate serial` - the reporter is admitted only if policy/serial.rego is."""
    import shutil

    os.makedirs(os.path.join(d, "bin"), exist_ok=True)
    for f in ("el-serial-emit.sh", "el-reporter.sh"):
        shutil.copy(os.path.join(ROOT, "guest", f), os.path.join(d, f))
    shutil.copy(el_serial_spec.SPEC_PATH, os.path.join(d, "el-serial-spec.json"))
    for name, body in STUB_TOOLS.items():
        p = os.path.join(d, "bin", name)
        with open(p, "w") as f:
            f.write(f"#!/bin/sh\n{body}\n")
        os.chmod(p, 0o755)
    with open(os.path.join(d, "bin", "el-serial-emit"), "w") as f:
        f.write('#!/bin/sh\nexec sh "$BUNDLE/el-serial-emit.sh" "$@"\n')
    os.chmod(os.path.join(d, "bin", "el-serial-emit"), 0o755)
    files = {
        "meminfo": "MemTotal: 716800 kB\nMemAvailable: 402112 kB\nSwapTotal: 358400 kB\nSwapFree: 358400 kB\n",
        "mm_stat": "1000 400 0 0 0 0 0 0 0\n",
        "guest.json": '{"deb_sha256":"'
        + "0" * 64
        + '","git_rev":"stub","snapshot":"20260920T000000Z"}\n',
        "appletsrc": "[Containments][1][Wallpaper][org.kde.image][General]\nImage=EL-Openglo\n",
        "sddm.conf": "[Theme]\nCurrent=el-openglo-openglo\n",
    }
    for name, text in files.items():
        with open(os.path.join(d, name), "w") as f:
            f.write(text)
    sh = [
        "#!/bin/sh",
        "# GENERATED by scripts/el_serial_emit.py --reporter-bundle (W237); do not hand-edit.",
        "set -eu",
        'BUNDLE=$(cd "$(dirname "$0")" && pwd)',
        "export BUNDLE",
        'export PATH="$BUNDLE/bin:$PATH" EL_SERIAL_SPEC="$BUNDLE/el-serial-spec.json"',
        'export EL_MEMINFO_FILE="$BUNDLE/meminfo" EL_ZRAM_MM_STAT="$BUNDLE/mm_stat" EL_GUEST_JSON="$BUNDLE/guest.json"',
        'export EL_APPLETSRC="$BUNDLE/appletsrc" EL_SDDM_CONF_DIR="$BUNDLE" EL_WAIT_S=1 EL_SETTLE_CAP_S=1',
        'mkdir -p "$BUNDLE/sddm.d"',
        'cp "$BUNDLE/sddm.conf" "$BUNDLE/sddm.d/x.conf"',
        'export EL_SDDM_CONF_DIR="$BUNDLE/sddm.d"',
        "OUT=$(mktemp)",
    ]
    for i, p in enumerate(probes):
        boot = f"{i:08x}-0000-4000-8000-000000000000"
        sh += [
            f'W=$(mktemp -d); echo "{boot}" > "$W/boot"; echo "BOOT_IMAGE=/vmlinuz quiet el.probe={p}" > "$W/cmdline"',
            'echo "100.00 0.00" > "$W/uptime"',
            (
                'EL_SERIAL_DEV="$OUT" EL_SERIAL_RUN="$W" EL_SERIAL_BOOT_FILE="$W/boot" EL_SERIAL_UPTIME_FILE="$W/uptime" '
                'EL_CMDLINE_FILE="$W/cmdline" sh "$BUNDLE/el-reporter.sh" system'
            ),
            'EL_SERIAL_DEV="$OUT" EL_SERIAL_RUN="$W" EL_SERIAL_BOOT_FILE="$W/boot" EL_SERIAL_UPTIME_FILE="$W/uptime" '
            'EL_CMDLINE_FILE="$W/cmdline" XDG_SESSION_TYPE=wayland sh "$BUNDLE/el-reporter.sh" session'
            if p in ("P1", "P2", "P4")
            else ":",
        ]
    sh += ['cat "$OUT"']
    with open(os.path.join(d, "run.sh"), "w") as f:
        f.write("\n".join(sh) + "\n")
    return list(probes)


def interleave(lines):
    """Records among console noise, as ttyS0 carries them; \\r\\n as ONLCR writes it."""
    out = []
    for i, line in enumerate(lines):
        out.append(NOISE[i % len(NOISE)])
        out.append(line)
    out.append(NOISE[-1])
    return "".join(x + "\r\n" for x in out).encode()


def fixtures():
    """{name: bytes}: clean / gap / corrupt / noise-only."""
    clean = p2_boot()
    gap = [x for x in clean if not x.startswith("@@EL1 1 ")]  # drop seq 1 (an el.mem)
    corrupt = list(clean)
    i = next(k for k, x in enumerate(corrupt) if " blob.part " in x)
    j = corrupt[i].index('"b64":"') + len('"b64":"') + 10
    corrupt[i] = (
        corrupt[i][:j] + ("A" if corrupt[i][j] != "A" else "B") + corrupt[i][j + 1 :]
    )
    return {
        "clean.log": interleave(clean),
        "gap.log": interleave(gap),
        "corrupt.log": interleave(corrupt),
        "noise-only.log": "".join(x + "\r\n" for x in NOISE * 3).encode(),
    }


def write_fixtures(d):
    os.makedirs(d, exist_ok=True)
    for name, data in sorted(fixtures().items()):
        tmp = os.path.join(d, name + ".tmp")
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, os.path.join(d, name))
        print(
            f"el_serial_emit: wrote {os.path.relpath(os.path.join(d, name), ROOT)} ({len(data)} bytes)"
        )


def _selftest():
    import read_serial

    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    lines = p2_boot()
    doc = read_serial.measure("".join(x + "\n" for x in lines).encode(), "<round-trip>")
    c = doc["cases"][0] if doc["cases"] else {}
    chk("round trip: one boot read back", len(doc["cases"]), 1)
    chk("round trip: every frame read back", c.get("frames"), len(lines))
    chk("round trip: no withheld fact", c.get("withheld"), [])
    chk(
        "round trip: el.done records == frames before it",
        (c.get("done") or {}).get("records"),
        len(lines) - 1,
    )
    chk("round trip: four blobs verified", len(c.get("blobs", [])), 4)
    e = Emitter(BOOT, _ticker())
    try:
        e.frame("el.mem", mem_total_kb=1)
        chk("writer refuses a payload missing keys", False, True)
    except ValueError:
        chk("writer refuses a payload missing keys", True, True)
    try:
        e.frame("el.settled", capped=False, extra=1)
        chk("writer refuses an extra key", False, True)
    except ValueError:
        chk("writer refuses an extra key", True, True)
    try:
        e.frame("el.oom", comm="x" * 2000, pid=1, mem_available_kb=0)
        chk("writer refuses a line over max_line_bytes", False, True)
    except ValueError:
        chk("writer refuses a line over max_line_bytes", True, True)
    chk(
        "an empty blob is ONE part with empty b64",
        (e.blob("empty", b""), e.lines[-2].count('"b64":""')),
        ("b0", 1),
    )
    for name, data in sorted(fixtures().items()):
        p = os.path.join(FIXTURES, name)
        committed = None
        if os.path.isfile(p):
            with open(p, "rb") as fh:
                committed = fh.read()
        chk(
            f"committed {name} == regenerated",
            committed is not None and committed == data,
            True,
        )
    ref, _times = op_reference(p2_ops())
    rdoc = read_serial.measure(
        "".join(x + "\n" for x in ref).encode(), "<op-reference>"
    )
    rc = rdoc["cases"][0] if rdoc["cases"] else {}
    chk(
        "the op-clocked reference reads back whole (P2, four blobs)",
        (len(rdoc["cases"]), rc.get("withheld"), len(rc.get("blobs", []))),
        (1, [], 4),
    )
    import shutil
    import subprocess
    import tempfile

    if not (shutil.which("jq") and shutil.which("flock")):
        print(
            "  SKIP the sh writer vs the reference, and the reporter per probe: jq or flock absent on this "
            "machine (2 skipped; luthen-observability checks.serial_writer runs the `--sh-bundle` and "
            "`--reporter-bundle` run.sh where they exist)"
        )
    else:
        with tempfile.TemporaryDirectory() as td:
            sh_bundle(td)
            r = subprocess.run(
                ["sh", os.path.join(td, "run.sh")],
                capture_output=True,
                text=True,
                check=False,
            )
            chk(
                "the sh writer's log is byte-equal to the reference writer's",
                (r.returncode, r.stderr[-300:]),
                (0, ""),
            )
        with tempfile.TemporaryDirectory() as td:
            ps = reporter_bundle(td)
            r = subprocess.run(
                ["sh", os.path.join(td, "run.sh")], capture_output=True, check=False
            )
            rd = read_serial.measure(r.stdout, "<reporter>")
            chk(
                "the reporter's log reads back one clean boot per probe",
                (
                    r.returncode,
                    sorted(c.get("probe") for c in rd["cases"]),
                    [c.get("withheld") for c in rd["cases"]],
                ),
                (0, sorted(ps), [[]] * len(ps)),
            )
    print("el_serial_emit selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    if argv[1:2] == ["--selftest"] and len(argv) == 2:
        return 0 if _selftest() else 1
    if argv[1:2] == ["--fixtures"] and len(argv) == 3:
        write_fixtures(argv[2])
        return 0
    if argv[1:2] == ["--sh-bundle"] and len(argv) == 3:
        n = sh_bundle(argv[2])
        print(
            f"el_serial_emit: wrote the sh-writer comparison bundle to {argv[2]} ({n} reference lines)"
        )
        return 0
    if argv[1:2] == ["--reporter-bundle"] and len(argv) == 3:
        ps = reporter_bundle(argv[2])
        print(
            f"el_serial_emit: wrote the reporter bundle to {argv[2]} (one boot each: {', '.join(ps)})"
        )
        return 0
    print(
        "usage: el_serial_emit.py --fixtures DIR | --sh-bundle DIR | --reporter-bundle DIR | --selftest",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
