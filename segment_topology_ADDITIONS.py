# [RECONSTRUCTED additions to segment_topology.py — the endpoints() + display_geom()
#  primitives promoted into the substrate in a later (compacted) session (⊕SUBSTRATE-
#  PRIMITIVES). APPEND these to the transcript-recovered segment_topology.py. NOTE: the
#  recovered base segment_topology.py is an EARLY version; the compacted sessions also
#  grew its GEOM22 / FORMATS(7,9,14,16,22) lattice / DIGITS16-LETTERS16-SYMBOLS16 glyph
#  tables / project(). Those later additions are NOT fully recoverable — only these two
#  primitives, which I have verbatim. Reconcile against the design log in COTYPE.md.]

def endpoints(key_or_spec):
    """Endpoint tuple (ax,ay,bx,by) for a GEOM22 segment key OR a raw spec.
    h -> (x0,y,x1,y); v -> (x,y0,x,y1); d -> (p0x,p0y,p1x,p1y)."""
    spec = GEOM22[key_or_spec] if isinstance(key_or_spec, str) else key_or_spec
    k = spec[0]
    if k == "h": return (spec[1], spec[3], spec[2], spec[3])
    if k == "v": return (spec[1], spec[2], spec[1], spec[3])
    if k == "d": return (spec[1][0], spec[1][1], spec[2][0], spec[2][1])
    raise ValueError(f"bad segment spec kind: {k!r}")


def display_geom(fmt):
    """POST-MERGE per-format display geometry, keyed by the names project() returns.
    A merged segment (e.g. 7-seg 'a' = a1|a2) spans the UNION of its parts' endpoints.
    This is the geometry a low-res surface renders in; keeps derez COVERAGE-MONOTONE
    (the renderer must use project()'s own key space)."""
    merge = FORMATS[fmt]["merge"]
    geo = {}
    for k in FORMATS[fmt]["mask"]:
        tgt = merge.get(k, k)
        e = endpoints(k)
        if tgt not in geo:
            geo[tgt] = list(e)
        else:
            xs = [geo[tgt][0], geo[tgt][2], e[0], e[2]]
            ys = [geo[tgt][1], geo[tgt][3], e[1], e[3]]
            geo[tgt] = [min(xs), min(ys), max(xs), max(ys)]
    return geo
