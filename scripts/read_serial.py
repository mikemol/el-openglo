#!/usr/bin/env python3
"""read_serial.py — the READER of el-serial/1 (catalog/guest-image.md (f)).

A guest's ttyS0 log (kernel printk, systemd, plymouth, getty, and our `@@EL1`
frames) in; the MEASUREMENT out. It judges nothing: policy/serial.rego decides
(per-probe required kinds, a boot with no el.done). Joined by
`scripts/opa_gate.py serial LOG`.

    scripts/read_serial.py --json LOG    # the facts, for opa
    scripts/read_serial.py --list LOG    # one line per boot, n of m; REFUSES (exit 1) an empty population
    scripts/read_serial.py --selftest    # the measurement can SEE each defect it reports

What it measures, per boot (a boot = frames sharing one `boot` value that has an
el.ident): sequence gaps, duplicates and reordering; every frame's grammar, canonical
JSON and exact key set against guest/el-serial-spec.json; blob reassembly with the
part discipline and sha256 + byte-count verification; references to blobs; el.done's
count against its own SEQ and frames after it. Every defect is a `withheld` string
on the case, and a withheld case reports NO blobs: never partial data. Frames that
cannot be assigned to a boot with an el.ident are log-level `withheld`. A log with no
el.ident has an empty population (`cases: []`).

Weakness: it sees only what reached the log. A frame lost AFTER the last one received
is invisible unless el.done is missing (which the policy denies) — the tail is covered
by el.done, not by this reader. And sha256 proves the blob is the bytes the guest
hashed, not that the guest read the right file.
"""
import base64
import binascii
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import el_serial_spec  # noqa: E402

ROOT = el_serial_spec.ROOT


class _Dup(ValueError):
    pass


def _no_dups(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise _Dup("duplicate key")
    return dict(pairs)


def _ranges(nums):
    out, nums = [], sorted(nums)
    for n in nums:
        if out and out[-1][1] == n - 1:
            out[-1][1] = n
        else:
            out.append([n, n])
    return out


def _parse(spec, text, raw_len):
    """(seq, kind, obj, errs) or (None, None, None, reason) when unassignable."""
    m = re.fullmatch(re.escape(spec["marker"]) + r" (0|[1-9][0-9]*) ([a-z]+(?:\.[a-z]+)*) (\{.*\})", text)
    if not m:
        return None, None, None, "does not match `@@EL1 SEQ KIND JSON`"
    if raw_len > spec["max_line_bytes"]:
        return None, None, None, f"{raw_len} bytes > max_line_bytes {spec['max_line_bytes']}"
    try:
        obj = json.loads(m.group(3), object_pairs_hook=_no_dups)
    except ValueError as e:
        return None, None, None, f"JSON does not parse ({e})"
    if not isinstance(obj, dict) or not el_serial_spec.type_ok(spec, "boot_id", obj.get("boot")):
        return None, None, None, "no valid `boot`"
    seq, kind, errs = int(m.group(1)), m.group(2), []
    if el_serial_spec.canonical(obj) != m.group(3):
        errs.append(f"seq {seq}: JSON is not canonical (sorted keys at every level, no spaces, ASCII)")
    errs += [f"seq {seq}: {e}" for e in el_serial_spec.validate(spec, kind, obj)]
    return seq, kind, obj, errs


def _blobs(spec, frames, withheld):
    """Walk well-formed frames in SEQ order; {id: blob} of the verified ones."""
    w, verified, cur = spec["part_b64_chars"], {}, None
    for seq, kind, obj in frames:
        if kind == "blob.part":
            if cur is None:
                if obj["n"] != 0 or obj["id"] != f"b{seq}":
                    withheld.append(f"seq {seq}: blob.part {obj['id']} n={obj['n']} opens no blob (first part must be n=0 with id b<its SEQ>)")
                    continue
                cur = {"id": obj["id"], "of": obj["of"], "parts": []}
            if obj["id"] != cur["id"] or obj["n"] != len(cur["parts"]) or obj["of"] != cur["of"]:
                withheld.append(f"seq {seq}: blob.part {obj['id']} n={obj['n']}/{obj['of']} breaks blob {cur['id']} at part {len(cur['parts'])}/{cur['of']}")
                cur = None
                continue
            last = obj["n"] == obj["of"] - 1
            L = len(obj["b64"])
            if obj["n"] >= obj["of"] or (not last and L != w) or (last and L == 0 and obj["of"] != 1):
                withheld.append(f"seq {seq}: blob.part {obj['id']} n={obj['n']}/{obj['of']} has {L} b64 chars (non-final parts are exactly {w}; only a one-part blob may be empty)")
                cur = None
                continue
            cur["parts"].append(obj["b64"])
        elif kind == "blob.end":
            if cur is None or obj["id"] != cur["id"] or obj["of"] != cur["of"] or len(cur["parts"]) != cur["of"]:
                withheld.append(f"seq {seq}: blob.end {obj['id']} does not close a complete blob")
                cur = None
                continue
            try:
                data = base64.b64decode("".join(cur["parts"]), validate=True)
            except (binascii.Error, ValueError):
                withheld.append(f"seq {seq}: blob {obj['id']}: base64 does not decode")
                cur = None
                continue
            sha = hashlib.sha256(data).hexdigest()
            if sha != obj["sha256"] or len(data) != obj["bytes"]:
                withheld.append(f"seq {seq}: blob {obj['id']} ({obj['label']}): sha256/bytes mismatch — got {sha[:12]}…/{len(data)}, declared {obj['sha256'][:12]}…/{obj['bytes']}")
            else:
                verified[obj["id"]] = {"id": obj["id"], "label": obj["label"], "bytes": len(data), "sha256": sha}
            cur = None
        else:
            if cur is not None:
                withheld.append(f"seq {seq}: {kind} interrupts blob {cur['id']} (a blob's parts and end are consecutive)")
                cur = None
            for k, t in sorted(spec["kinds"][kind].items()):
                if t == "blob" and obj[k] not in verified:
                    withheld.append(f"seq {seq}: {kind}.{k} references {obj[k]}, which is not a blob verified before it")
    if cur is not None:
        withheld.append(f"blob {cur['id']} never closed")
    return verified


def _case(spec, boot, frames):
    """frames: [(lineno, seq, kind, obj, errs)] in log order."""
    withheld = [e for fr in frames for e in fr[4]]
    seqs = [fr[1] for fr in frames]
    for s in sorted({s for s in seqs if seqs.count(s) > 1}):
        withheld.append(f"seq {s} appears {seqs.count(s)} times")
    if any(b <= a for a, b in zip(seqs, seqs[1:])):
        withheld.append("SEQ is not increasing in log order")
    for a, b in _ranges(set(range(max(seqs) + 1)) - set(seqs)):
        withheld.append(f"gap: seq {a}" + (f"–{b}" if b != a else "") + " missing")
    good = sorted({fr[1]: fr for fr in frames if not fr[4]}.values(), key=lambda fr: fr[1])
    idents = [fr for fr in good if fr[2] == "el.ident"]
    if len(idents) != 1 or idents[0][1] != 0:
        withheld.append(f"el.ident must be exactly one frame at seq 0 (found at seqs {[fr[1] for fr in idents]})")
    dones = [fr for fr in good if fr[2] == "el.done"]
    done = None
    if len(dones) > 1:
        withheld.append(f"el.done appears {len(dones)} times")
    if dones:
        d = dones[0]
        done = {"seq": d[1], "probe": d[3]["probe"], "records": d[3]["records"]}
        if d[3]["records"] != d[1]:
            withheld.append(f"el.done records={d[3]['records']} but its own SEQ is {d[1]} (records counts every frame before it)")
        after = sorted(s for s in seqs if s > d[1])
        if after:
            withheld.append(f"{len(after)} frame(s) after el.done (seq {after[0]}…)")
    verified = _blobs(spec, [fr[1:4] for fr in good], withheld)
    kinds = {}
    for fr in good:
        kinds[fr[2]] = kinds.get(fr[2], 0) + 1
    return {"boot": boot, "probe": idents[0][3]["probe"] if idents else None,
            "frames": len(frames), "seq_max": max(seqs), "kinds": kinds, "done": done,
            "blobs": [] if withheld else [verified[k] for k in sorted(verified, key=lambda b: int(b[1:]))],
            "withheld": withheld}


def measure(data, name):
    spec = el_serial_spec.load()
    marker = spec["marker"].encode()
    raws = data.split(b"\n")
    if raws and raws[-1] == b"":
        raws.pop()
    noise, log_withheld, boots, nframes = 0, [], {}, 0
    for i, raw in enumerate(raws, 1):
        raw = raw.rstrip(b"\r")
        if marker not in raw:
            noise += 1
            continue
        nframes += 1
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            log_withheld.append(f"line {i}: frame is not UTF-8")
            continue
        seq, kind, obj, errs = _parse(spec, text, len(raw))
        if seq is None:
            log_withheld.append(f"line {i}: malformed frame: {errs}")
            continue
        boots.setdefault(obj["boot"], []).append((i, seq, kind, obj, errs))
    cases = []
    for boot, frames in boots.items():
        if not any(fr[2] == "el.ident" and not fr[4] for fr in frames):
            log_withheld.append(f"boot {boot}: {len(frames)} frame(s) with no el.ident — not a case")
            continue
        cases.append(_case(spec, boot, frames))
    return {"protocol": spec["protocol"], "log": name, "lines": len(raws), "noise_lines": noise,
            "frame_lines": nframes, "cases": cases, "withheld": log_withheld}


def _list(doc):
    print(f"read_serial: {doc['log']}: {doc['frame_lines']} of {doc['lines']} lines are frames; "
          f"{len(doc['cases'])} boot(s)")
    for c in doc["cases"]:
        print(f"  {c['boot']} probe={c['probe']} frames={c['frames']} seq_max={c['seq_max']} "
              f"done={'yes' if c['done'] else 'NO'} blobs={len(c['blobs'])} withheld={len(c['withheld'])}")
        for w in c["withheld"]:
            print(f"    WITHHELD {w}")
    for w in doc["withheld"]:
        print(f"  WITHHELD {w}")
    clean = sum(1 for c in doc["cases"] if not c["withheld"])
    print(f"read_serial: {clean} of {len(doc['cases'])} boot(s) have no withheld fact")
    if not doc["cases"]:
        print("read_serial: REFUSE — no el.ident in the log; the population is empty, not the log clean", file=sys.stderr)
        return 1
    return 0


def _selftest():
    import el_serial_emit as em
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    def run(lines):
        return measure(em.interleave(lines), "<selftest>")

    def has(doc, needle):
        facts = doc["withheld"] + [w for c in doc["cases"] for w in c["withheld"]]
        return any(needle in w for w in facts)

    clean = em.p2_boot()
    d = run(clean)
    chk("clean: one case, no withheld, 4 blobs", (len(d["cases"]), d["cases"][0]["withheld"], len(d["cases"][0]["blobs"])), (1, [], 4))
    chk("clean: \\r\\n and noise lines are not frames", (d["noise_lines"], d["frame_lines"]), (len(clean) + 1, len(clean)))
    split = list(clean)
    split[3:4] = [split[3][:30], "[   12.345678] printk interleaved", split[3][30:]]
    d = run(split)
    chk("split record: malformed line withheld at log level", has(d, "malformed frame"), True)
    chk("split record: its SEQ is a gap", has(d, "gap: seq 3 missing"), True)
    chk("split record: a withheld case reports no blobs", d["cases"][0]["blobs"], [])
    flip = lambda m: '"sha256":"' + ("1" if m.group(1) == "0" else "0")  # noqa: E731 — still 64 hex
    bad = [re.sub(r'"sha256":"(.)', flip, x, count=1) if " blob.end " in x else x for x in clean]
    chk("bad sha256: mismatch withheld", has(run(bad), "sha256/bytes mismatch"), True)
    chk("noise only: empty population", run([])["cases"], [])
    chk("no el.ident: not a case, withheld at log level", (run(clean[1:])["cases"], has(run(clean[1:]), "no el.ident")), ([], True))
    e = em.Emitter(em.BOOT, em._ticker())
    e.frame("el.ident", guest={}, cmdline="", probe="P3")
    e.done("P3")
    e.frame("el.settled", capped=True)
    chk("frame after el.done: withheld", has(run(e.lines), "after el.done"), True)
    chk("non-canonical JSON: withheld", has(run(clean[:2] + [clean[2].replace('":', '": ', 1)] + clean[3:]), "not canonical"), True)
    chk("duplicate SEQ: withheld", has(run(clean[:2] + clean[1:]), "appears 2 times"), True)
    wrong = list(clean)
    wrong[-1] = wrong[-1].replace(f'"records":{len(clean) - 1}', '"records":3')
    chk("el.done records != its SEQ: withheld", has(run(wrong), "records=3"), True)
    unref = [x for x in clean if " el.journal " not in x]
    unref = [x.replace('"appletsrc":"b', '"appletsrc":"b9', 1) for x in unref]
    chk("reference to an unverified blob: withheld", has(run(unref), "not a blob verified before it"), True)
    for name, want in (("clean.log", 0), ("gap.log", 1), ("corrupt.log", 1), ("noise-only.log", None)):
        with open(os.path.join(em.FIXTURES, name), "rb") as f:
            d = measure(f.read(), name)
        got = None if not d["cases"] else min(1, len(d["cases"][0]["withheld"]))
        chk(f"fixture {name}: {'empty' if want is None else 'withheld' if want else 'clean'}", got, want)
    print("read_serial selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    if argv[1:] == ["--selftest"]:
        return 0 if _selftest() else 1
    if len(argv) == 3 and argv[1] in ("--json", "--list"):
        try:
            with open(argv[2], "rb") as f:
                data = f.read()
        except OSError as e:
            print(f"read_serial: cannot read {argv[2]}: {e}", file=sys.stderr)
            return 2
        doc = measure(data, argv[2])
        if argv[1] == "--json":
            print(json.dumps(doc, indent=1, sort_keys=True))
            return 0
        return _list(doc)
    bad = [a for a in argv[1:] if a.startswith("-") and a not in ("--json", "--list", "--selftest")]
    print(f"read_serial: unknown flag {bad[0]!r}" if bad else
          "usage: read_serial.py --json LOG | --list LOG | --selftest", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
