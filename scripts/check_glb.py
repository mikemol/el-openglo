#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_glb.py — the engine meshes are valid glTF binaries with the right named nodes (W152).

    scripts/check_glb.py            # the verdict, as opa_gate glb decides it
    scripts/check_glb.py --json     # the measurement policy/glb.rego decides
    scripts/check_glb.py --selftest # the measurement can see a bad header, a missing node, a drift

Per mesh make_glb declares: whether catalog/engines/<file> exists, whether its GLB
container parses (magic, version 2, declared length = file length, a JSON then a BIN
chunk), the node names it carries against the names the format's segment set
(segment_topology via make_glb.segments) or the matrix grid demands, every node whose
mesh has no triangles or a flat (zero-extent) bounding box, and whether the file is
byte-equal to a fresh emission.

WEAKNESS: it parses the container and the node/mesh/accessor references it uses; it
is not the Khronos glTF validator, and it proves the bytes match the emitter, not
that any engine imports them.
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))


def parse(data):
    """(gltf JSON dict, None) or (None, reason) - the GLB container read by its spec."""
    if len(data) < 20:
        return None, "shorter than a GLB header"
    magic, version, length = struct.unpack_from("<III", data, 0)
    if magic != 0x46546C67:
        return None, "magic is not glTF"
    if version != 2:
        return None, f"version {version}, not 2"
    if length != len(data):
        return None, f"declared length {length} != file length {len(data)}"
    jlen, jtype = struct.unpack_from("<II", data, 12)
    if jtype != 0x4E4F534A:
        return None, "first chunk is not JSON"
    try:
        doc = json.loads(data[20:20 + jlen])
    except ValueError as e:
        return None, f"JSON chunk unreadable: {e}"
    rest = 20 + jlen
    if rest + 8 > len(data) or struct.unpack_from("<II", data, rest)[1] != 0x004E4942:
        return None, "no BIN chunk after the JSON"
    return doc, None


def flat_nodes(doc):
    """Names of nodes whose mesh has no triangles or a bounding box flat in any axis."""
    out = []
    acc = doc.get("accessors", [])
    for n in doc.get("nodes", []):
        mesh = doc["meshes"][n["mesh"]] if "mesh" in n else None
        prims = mesh["primitives"] if mesh else []
        ok = bool(prims)
        for p in prims:
            pos, ind = acc[p["attributes"]["POSITION"]], acc[p.get("indices", -1)] if "indices" in p else None
            tris = (ind["count"] if ind else pos["count"]) // 3
            ok = ok and tris > 0 and all(hi > lo for lo, hi in zip(pos["min"], pos["max"]))
        if not ok:
            out.append(n.get("name", "?"))
    return out


def measure(out_dir=None):
    import make_glb as MG
    out_dir = out_dir or MG.OUT_DIR
    fresh = MG.documents()
    cases = []
    for name, (want, data) in sorted(fresh.items()):
        path = os.path.join(out_dir, name)
        if not os.path.exists(path):
            cases.append({"file": name, "present": False})
            continue
        raw = open(path, "rb").read()
        doc, why = parse(raw)
        case = {"file": name, "present": True, "parse_error": why, "current": raw == data,
                "want": sorted(want), "nodes": [], "flat": []}
        if doc is not None:
            case["nodes"] = sorted(n.get("name", "?") for n in doc.get("nodes", []))
            case["flat"] = flat_nodes(doc)
        cases.append(case)
    return {"cases": cases, "withheld": []}


def _selftest():
    import tempfile
    import make_glb as MG
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    docs = MG.documents()
    nodes, data = docs["el-seg7.glb"]
    doc, why = parse(data)
    chk("a fresh 7-seg mesh parses, with 7 named nodes and none flat",
        (why, sorted(n["name"] for n in doc["nodes"]), flat_nodes(doc)), (None, sorted("abcdefg"), []))
    chk("a bad magic is seen", parse(b"xxxx" + data[4:])[1], "magic is not glTF")
    chk("a truncated file is seen", parse(data[:-4])[1] is not None, True)
    with tempfile.TemporaryDirectory() as td:
        for name, (_n, d) in docs.items():
            open(os.path.join(td, name), "wb").write(d)
        m = measure(td)
        chk("a fresh tree is present and current everywhere",
            all(c["present"] and c["current"] and c["nodes"] == c["want"] for c in m["cases"]), True)
        os.remove(os.path.join(td, "el-seg16.glb"))
        open(os.path.join(td, "el-seg22.glb"), "wb").write(docs["el-seg7.glb"][1])
        m = {c["file"]: c for c in measure(td)["cases"]}
        chk("a missing file is absent; a wrong file is stale with the wrong nodes",
            (m["el-seg16.glb"]["present"], m["el-seg22.glb"]["current"], m["el-seg22.glb"]["nodes"] == m["el-seg22.glb"]["want"]),
            (False, False, False))
    print("check_glb selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    for a in argv[1:]:
        if a not in {"--json", "--selftest"}:
            print(f"check_glb: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate
    return opa_gate.gate("glb")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
