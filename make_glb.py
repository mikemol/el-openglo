#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""make_glb.py — the segment and matrix displays as glTF 2.0 binary meshes (W152).

    make_glb.py            # write catalog/engines/el-seg{7,16,22}.glb, el-matrix-5x7.glb
    make_glb.py --list     # the files and their node counts, nothing written

ONE NODE PER SEGMENT, NAMED BY ITS SEGMENT ID. An engine lights a glyph by
switching named nodes (or by the W153 shader reading a bitmask in node order), so
the node name IS the contract: segment_topology's ids, after the format's
projection (7-seg's a/d/g are the fused halves, exactly as FORMATS merges them).
The matrix is a 5x7 dot grid, nodes `r<row>c<col>`.

⚑ NO GEOMETRY IS AUTHORED HERE. The lattice is segment_topology.GEOM16 / geom22(),
the projections are FORMATS, and the stroke width and dot diameter are
MODULE_METRICS ratios of the digit height (H = 4 lattice units). This file only
thickens and extrudes.

Units: one lattice unit L = 1 metre-equivalent; the cell is 2 wide, 4 tall (6 for
22-seg's descender sub-cell), +Y up (the lattice's y is flipped), +Z toward the
viewer, depth = half the stroke.

WEAKNESS, STATED. Bars are boxes, not bevelled hexagonal segments; adjoining bars
overlap at the joints rather than mitring; no normals are emitted (engines flat-
shade or compute them); no material - colour is the W151 token file's job.
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_DIR = os.path.join(ROOT, "catalog", "engines")
SEG_FORMATS = ("7", "16", "22")
MATRIX = (5, 7)          # columns, rows: the EL-Matrix-5x7 font's grid
H = 4.0                  # digit height in lattice units


def _metrics():
    sys.path.insert(0, ROOT)
    import segment_topology as ST
    return ST, ST.metrics(H)


def segments(fmt):
    """{segment id: (kind, endpoints)} for a format: the 16/22 lattice projected
    through FORMATS[fmt] (masked out dropped, merged halves fused to one bar)."""
    ST, _m = _metrics()
    lattice = ST.geom22() if fmt == "22" else ST.GEOM16
    f = ST.FORMATS[fmt]
    out = {}
    for sid, g in lattice.items():
        if sid not in f["mask"]:
            continue
        name = f["merge"].get(sid, sid)
        if g[0] == "h":
            p0, p1 = (g[1], g[3]), (g[2], g[3])
        elif g[0] == "v":
            p0, p1 = (g[1], g[2]), (g[1], g[3])
        else:
            p0, p1 = g[1], g[2]
        if name in out:      # a merge: the fused halves are collinear; span both
            pts = out[name] + [p0, p1]
            out[name] = [min(pts), max(pts)]
        else:
            out[name] = [p0, p1]
    return out


def _box(p0, p1, half, depth):
    """8 vertices and 36 indices: the bar p0-p1 thickened by `half` each side
    (a point becomes a square) and extruded `depth` toward +Z."""
    (x0, y0), (x1, y1) = p0, p1
    y0, y1 = -y0, -y1
    dx, dy = x1 - x0, y1 - y0
    n = (dx * dx + dy * dy) ** 0.5
    if n == 0:
        ux, uy = 1.0, 0.0
        x0, x1 = x0 - half, x1 + half
    else:
        ux, uy = dx / n, dy / n
    px, py = -uy * half, ux * half
    quad = [(x0 + px, y0 + py), (x1 + px, y1 + py), (x1 - px, y1 - py), (x0 - px, y0 - py)]
    verts = [(x, y, 0.0) for x, y in quad] + [(x, y, depth) for x, y in quad]
    faces = [(4, 5, 6), (4, 6, 7), (0, 2, 1), (0, 3, 2)]
    for i in range(4):
        j = (i + 1) % 4
        faces += [(i, j, j + 4), (i, j + 4, i + 4)]
    return verts, [k for f in faces for k in f]


def glb(parts):
    """A glTF 2.0 binary from [(node name, verts, indices)]: one mesh per node."""
    blob = bytearray()
    views, accessors, meshes, nodes = [], [], [], []
    for name, verts, idx in parts:
        off = len(blob)
        for v in verts:
            blob += struct.pack("<3f", *v)
        views.append({"buffer": 0, "byteOffset": off, "byteLength": len(blob) - off, "target": 34962})
        accessors.append({"bufferView": len(views) - 1, "componentType": 5126, "count": len(verts), "type": "VEC3",
                          "min": [min(v[i] for v in verts) for i in range(3)],
                          "max": [max(v[i] for v in verts) for i in range(3)]})
        off = len(blob)
        for i in idx:
            blob += struct.pack("<H", i)
        views.append({"buffer": 0, "byteOffset": off, "byteLength": len(blob) - off, "target": 34963})
        accessors.append({"bufferView": len(views) - 1, "componentType": 5123, "count": len(idx), "type": "SCALAR"})
        blob += b"\0" * (-len(blob) % 4)
        meshes.append({"name": name, "primitives": [{"attributes": {"POSITION": len(accessors) - 2},
                                                      "indices": len(accessors) - 1}]})
        nodes.append({"name": name, "mesh": len(meshes) - 1})
    doc = {"asset": {"version": "2.0", "generator": "el-openglo make_glb.py (W152)"},
           "scene": 0, "scenes": [{"nodes": list(range(len(nodes)))}],
           "nodes": nodes, "meshes": meshes, "accessors": accessors,
           "bufferViews": views, "buffers": [{"byteLength": len(blob)}]}
    js = json.dumps(doc, separators=(",", ":"), sort_keys=True).encode()
    js += b" " * (-len(js) % 4)
    body = struct.pack("<II", len(js), 0x4E4F534A) + js + struct.pack("<II", len(blob), 0x004E4942) + bytes(blob)
    return struct.pack("<III", 0x46546C67, 2, 12 + len(body)) + body


def documents():
    """{file name: (node names, glb bytes)} - every display this emitter writes."""
    _ST, m = _metrics()
    half, dot = m["stroke"] / 2, m["dot"] / 2
    out = {}
    for fmt in SEG_FORMATS:
        segs = segments(fmt)
        parts = [(sid, *_box(p0, p1, half, half)) for sid, (p0, p1) in sorted(segs.items())]
        out[f"el-seg{fmt}.glb"] = ([p[0] for p in parts], glb(parts))
    cols, rows = MATRIX
    pitch = 2.0 / (cols - 1)       # the matrix spans the segment cell's 2-unit width
    parts = []
    for r in range(rows):
        for c in range(cols):
            p = (c * pitch, r * pitch)
            parts.append((f"r{r}c{c}", *_box(p, p, dot, dot)))
    out[f"el-matrix-{cols}x{rows}.glb"] = ([p[0] for p in parts], glb(parts))
    return out


def main(argv):
    for a in argv[1:]:
        if a != "--list":
            print(f"make_glb: unknown flag {a!r}", file=sys.stderr)
            return 2
    docs = documents()
    if "--list" in argv:
        for name, (nodes, data) in sorted(docs.items()):
            print(f"  {name:22s} {len(nodes):3d} nodes  {len(data)} bytes")
        return 0
    from emitters import atomic_write
    os.makedirs(OUT_DIR, exist_ok=True)
    for name, (_nodes, data) in sorted(docs.items()):
        atomic_write(os.path.join(OUT_DIR, name), data)
    print(f"make_glb: wrote {len(docs)} of {len(docs)} meshes to {os.path.relpath(OUT_DIR, ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
