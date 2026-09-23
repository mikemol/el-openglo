#!/usr/bin/env python3
"""el_serial_emit.py — the pure-Python REFERENCE writer of el-serial/1.

The guest runs guest/el-serial-emit.sh (POSIX sh + jq; there is no Python in the
guest). This file implements the same spec, catalog/guest-image.md (f), on the
host, so the round trip (emit a boot, read it back with read_serial.py) can be
proved here, and so the fixtures under catalog/fixtures/serial/ are generated,
not hand-typed. Both writers take every kind, payload key and type from
guest/el-serial-spec.json (through el_serial_spec here, through jq there).

    scripts/el_serial_emit.py --fixtures DIR   # write the four fixtures into DIR
    scripts/el_serial_emit.py --selftest       # round trip + committed fixtures == regenerated

Weakness: this proves the Python writer and the reader agree. It does NOT run
the sh writer (jq is not on this host); the sh writer shares the table, not the
code, and is only syntax-checked (`sh -n`). The first guest boot (W71e) is
where the sh writer's bytes meet this reader.
"""
import base64
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import el_serial_spec  # noqa: E402

ROOT = el_serial_spec.ROOT
FIXTURES = os.path.join(ROOT, "catalog", "fixtures", "serial")


class Emitter:
    """One boot's writer. `clock()` returns centiseconds since boot (int)."""

    def __init__(self, boot, clock, spec=None):
        self.spec = spec or el_serial_spec.load()
        self.boot, self.clock, self.seq, self.lines = boot, clock, 0, []

    def frame(self, kind, **payload):
        if set(payload) & set(self.spec["envelope"]):
            raise ValueError(f"{kind}: payload must not carry the envelope keys {sorted(self.spec['envelope'])}")
        obj = dict(payload, boot=self.boot, t=self.clock())
        errs = el_serial_spec.validate(self.spec, kind, obj)
        if errs:
            raise ValueError("; ".join(errs))
        line = f"{self.spec['marker']} {self.seq} {kind} {el_serial_spec.canonical(obj)}"
        if len(line.encode()) > self.spec["max_line_bytes"]:
            raise ValueError(f"{kind}: {len(line.encode())} bytes > {self.spec['max_line_bytes']}; send it as a blob")
        self.seq += 1
        self.lines.append(line)
        return line

    def blob(self, label, data):
        """blob.part 0..of-1 then blob.end, consecutive (one lock hold). Returns the id."""
        bid = f"b{self.seq}"
        b64 = base64.b64encode(data).decode()
        w = self.spec["part_b64_chars"]
        parts = [b64[i:i + w] for i in range(0, len(b64), w)] or [""]
        for n, chunk in enumerate(parts):
            self.frame("blob.part", id=bid, n=n, of=len(parts), b64=chunk)
        self.frame("blob.end", id=bid, sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                   of=len(parts), label=label)
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
    e.frame("el.ident", guest={"deb_sha256": "0" * 64, "git_rev": "4abcb5b", "snapshot": "20260920T000000Z"},
            cmdline="BOOT_IMAGE=/vmlinuz quiet splash console=tty0 console=ttyS0 el.probe=P2", probe="P2")
    mem = dict(mem_total_kb=716800, mem_available_kb=402112, swap_total_kb=358400, swap_free_kb=358400,
               zram_orig_bytes=0, zram_compr_bytes=0)
    e.frame("el.mem", **mem)
    e.frame("el.session", uid=1000, session_type="wayland")
    e.frame("el.settled", capped=False)
    j = {name: e.blob(f"journal.{name}", ("\n".join(f'{{"MESSAGE":"{name} line {i}"}}' for i in range(40))).encode())
         for name in ("sddm", "plasmashell", "plymouth")}
    e.frame("el.journal", **j)
    f = e.blob("appletsrc", b"[Containments][1][Wallpaper][org.kde.image][General]\nImage=EL-Openglo\n" * 20)
    e.frame("el.file", appletsrc=f)
    e.frame("el.mem", **dict(mem, mem_available_kb=198656))
    e.done("P2")
    return e.lines


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
    corrupt[i] = corrupt[i][:j] + ("A" if corrupt[i][j] != "A" else "B") + corrupt[i][j + 1:]
    return {"clean.log": interleave(clean), "gap.log": interleave(gap),
            "corrupt.log": interleave(corrupt), "noise-only.log": "".join(x + "\r\n" for x in NOISE * 3).encode()}


def write_fixtures(d):
    os.makedirs(d, exist_ok=True)
    for name, data in sorted(fixtures().items()):
        tmp = os.path.join(d, name + ".tmp")
        with open(tmp, "wb") as f:
            f.write(data)
        os.replace(tmp, os.path.join(d, name))
        print(f"el_serial_emit: wrote {os.path.relpath(os.path.join(d, name), ROOT)} ({len(data)} bytes)")


def _selftest():
    import read_serial
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    lines = p2_boot()
    doc = read_serial.measure("".join(x + "\n" for x in lines).encode(), "<round-trip>")
    c = doc["cases"][0] if doc["cases"] else {}
    chk("round trip: one boot read back", len(doc["cases"]), 1)
    chk("round trip: every frame read back", c.get("frames"), len(lines))
    chk("round trip: no withheld fact", c.get("withheld"), [])
    chk("round trip: el.done records == frames before it", (c.get("done") or {}).get("records"), len(lines) - 1)
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
    chk("an empty blob is ONE part with empty b64", (e.blob("empty", b""), e.lines[-2].count('"b64":""')), ("b0", 1))
    for name, data in sorted(fixtures().items()):
        p = os.path.join(FIXTURES, name)
        chk(f"committed {name} == regenerated", os.path.isfile(p) and open(p, "rb").read() == data, True)
    print("el_serial_emit selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    if argv[1:2] == ["--selftest"] and len(argv) == 2:
        return 0 if _selftest() else 1
    if argv[1:2] == ["--fixtures"] and len(argv) == 3:
        write_fixtures(argv[2])
        return 0
    print("usage: el_serial_emit.py --fixtures DIR | --selftest", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
