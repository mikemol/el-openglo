# METADATA
# title: "D0 — an empty registry admits nothing"
# description: |
#   The measurement is `scripts/check_display_registry.py --json`: the round trip
#   of display_types.as_qml_js() against registry(), and the registry's
#   population — segGeom strokes, segGlyphs formats (each glyph beside the
#   substrate's projection), font5x7 glyphs (column bytes), displays. An empty
#   population — or an empty KIND of it — is a registry not built, not an
#   emission faithful.
package el.display_registry

import rego.v1

kinds := {"stroke", "format", "matrix", "display"}

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "D0: no registry entry was measured; the registry is not built, not the emission faithful"
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	some k in kinds
	count([c | some c in input.cases; c.kind == k]) == 0
	msg := sprintf("D0: the registry has no %s entries — an empty population, not an agreeing registry", [k])
}

# ⚑ EVERY CASE LANDS IN EXACTLY ONE OF withheld / deny / admitted.
# check_display_registry.py ALWAYS emits `roundtrip` (an object with a boolean
# `parsed` and a `keys` array whose entries carry boolean emitted / registry /
# equal); per case a `kind`, and per kind: stroke `in_substrate` (boolean),
# format `glyphs` (array; each glyph's `emitted` an array — its `substrate` is
# LEGITIMATELY null, meaning "in no table", which D2 judges), matrix `cols`
# (array). A null or absent one is "could not say" and is withheld (D5), never
# judged: `not input.roundtrip` DENIED a null round trip, `not k.emitted` DENIED
# a null emitted, and `not c.in_substrate` DENIED a null in_substrate; a null
# `cols` fell through every D3 rule and was silently ADMITTED.

rt_obj := r if {
	r := object.get(input, "roundtrip", null)
	is_object(r)
}

rt_keys := ks if {
	ks := object.get(rt_obj, "keys", null)
	is_array(ks)
} else := []

# METADATA
# title: "D5 — a round trip that was not measured is withheld, not denied"
withheld contains msg if {
	count(object.get(input, "cases", [])) > 0
	not rt_obj
	msg := "D5: the round trip was not measured"
}

withheld contains msg if {
	not is_boolean(object.get(rt_obj, "parsed", null))
	msg := "D5: roundtrip.parsed was not measured"
}

withheld contains msg if {
	not is_array(object.get(rt_obj, "keys", null))
	msg := "D5: roundtrip.keys was not measured"
}

# the round-trip fields each key's verdict actually consults
rt_unmeasured(k) := ({"emitted" | not is_boolean(object.get(k, "emitted", null))} | {"registry" |
	k.emitted == true
	not is_boolean(object.get(k, "registry", null))
}) | {"equal" |
	k.emitted == true
	k.registry == true
	not is_boolean(object.get(k, "equal", null))
}

withheld contains msg if {
	some k in rt_keys
	count(rt_unmeasured(k)) > 0
	msg := sprintf("D5: roundtrip %v: %v was not measured", [object.get(k, "key", "?"), sort(rt_unmeasured(k))])
}

case_key(c) := sprintf("%v:%v", [object.get(c, "kind", null), object.get(c, "id", null)])

field_type := {"stroke": {"in_substrate": "boolean"}, "format": {"glyphs": "array"}, "matrix": {"cols": "array"}, "display": {}}

unmeasured(c) := {"kind"} if {
	not object.get(c, "kind", null) in kinds
} else := ({f |
	some f, t in field_type[c.kind]
	type_name(object.get(c, f, null)) != t
} | {sprintf("glyphs[%d].emitted", [i]) |
	c.kind == "format"
	gs := object.get(c, "glyphs", null)
	is_array(gs)
	some i, g in gs
	not is_array(object.get(g, "emitted", null))
}) | {sprintf("glyphs[%d].substrate", [i]) |
	# substrate is legitimately null ("in no table"), but it is always emitted
	c.kind == "format"
	gs := object.get(c, "glyphs", null)
	is_array(gs)
	some i, g in gs
	not "substrate" in object.keys(g)
}

measured_case(c) if count(unmeasured(c)) == 0

measured_cases contains c if {
	some c in object.get(input, "cases", [])
	measured_case(c)
}

# METADATA
# title: "D5 — a case with an unmeasured field is withheld, not judged"
withheld contains msg if {
	some c in object.get(input, "cases", [])
	count(unmeasured(c)) > 0
	msg := sprintf("D5: %s: %v was not measured", [case_key(c), sort(unmeasured(c))])
}

# METADATA
# title: "D1 — as_qml_js() parses back to registry(), key for key"
# description: |
#   A serialisation that drops or mangles a table is the failure a byte-count
#   cannot see. The emission is JSON by construction, so it is parsed back and
#   compared — a round trip, not a re-derivation.
deny contains msg if {
	input.roundtrip.parsed == false
	msg := sprintf("D1: as_qml_js is not parseable: %s", [input.roundtrip.error])
}

deny contains msg if {
	some k in rt_keys
	k.emitted == false
	msg := sprintf("D1: %s: emitted registry is missing it", [k.key])
}

deny contains msg if {
	some k in rt_keys
	k.emitted == true
	k.registry == false
	msg := sprintf("D1: %s: emitted registry invents it", [k.key])
}

deny contains msg if {
	some k in rt_keys
	k.emitted == true
	k.registry == true
	k.equal == false
	msg := sprintf("D1: %s: emitted value differs from registry()", [k.key])
}

# METADATA
# title: "D2 — the registry's glyphs and strokes agree with the substrate"
# description: |
#   A registry that round-trips perfectly while disagreeing with
#   segment_topology is internally consistent and wrong. Each emitted glyph must
#   equal the substrate's projection at its format; each stroke must be one
#   GEOM22 defines.
defect contains {"case": sprintf("format:%s", [c.id]), "msg": msg} if {
	some c in measured_cases
	c.kind == "format"
	some g in c.glyphs
	g.substrate == null
	msg := sprintf("D2: segGlyphs[%s][%q] is in no substrate table", [c.id, g.ch])
}

defect contains {"case": sprintf("format:%s", [c.id]), "msg": msg} if {
	some c in measured_cases
	c.kind == "format"
	some g in c.glyphs
	g.substrate != null
	g.emitted != g.substrate
	msg := sprintf("D2: segGlyphs[%s][%q] = %v but the substrate projects %v", [c.id, g.ch, g.emitted, g.substrate])
}

defect contains {"case": sprintf("stroke:%s", [c.id]), "msg": msg} if {
	some c in measured_cases
	c.kind == "stroke"
	c.in_substrate == false
	msg := sprintf("D2: segGeom names %q, which GEOM22 does not define", [c.id])
}

# METADATA
# title: "D3 — no matrix glyph contradicts the font it belongs to"
# description: |
#   A WRONG GLYPH ROUND-TRIPS PERFECTLY. 'A' shipped as 0x7e,0x11,0x11,0x11,0x7e
#   — crossbar on row 4, flat apex — while every check was green, and only
#   rendering the marquee and LOOKING caught it. So this asks what a picture
#   asks: do the glyphs agree about where this 5x7 font's shared features sit?
#   Relations WITHIN the set, not typographic truths: a letter wrong the way
#   every other letter is wrong passes (the stated weakness). '0' is NOT in the
#   symmetric set: its slashed diagonal (0x3e,0x51,0x49,0x45,0x3e) is the
#   feature that tells it from 'O', and listing it was the instrument being
#   wrong about the world before the artifact was.
symmetric := {"A", "H", "O", "T", "U", "V", "W", "X", "M"}

matrix[ch] := c.cols if {
	some c in measured_cases
	c.kind == "matrix"
	ch := c.id
}

# every matrix id the registry carries, measured or not: an unmeasured 'A' is
# withheld (D5), not "absent from the font"
matrix_ids contains c.id if {
	some c in object.get(input, "cases", [])
	c.kind == "matrix"
}

lit(cols, row) := count([i | some i, b in cols; bits.and(b, bits.lsh(1, row)) != 0])

rows_with(cols, n) := sort([row | some row in numbers.range(0, 6); lit(cols, row) >= n])

full_rows(cols) := sort([row | some row in numbers.range(0, 6); lit(cols, row) == 5])

defect contains {"case": sprintf("matrix:%s", [ch]), "msg": msg} if {
	some ch, cols in matrix
	count(cols) != 5
	msg := sprintf("D3: %q: %d columns, not 5", [ch, count(cols)])
}

defect contains {"case": sprintf("matrix:%s", [ch]), "msg": msg} if {
	some ch, cols in matrix
	some i, b in cols
	bits.and(b, bits.negate(127)) != 0
	msg := sprintf("D3: %q column %d = %d lights a row past 7", [ch, i, b])
}

# the crossbar family: A and H carry a full-width bar on the middle row (3)
defect contains {"case": sprintf("matrix:%s", [ch]), "msg": msg} if {
	count(object.get(input, "cases", [])) > 0
	some ch in {"A", "H"}
	not ch in matrix_ids
	msg := sprintf("D3: %q: absent from the font", [ch])
}

defect contains {"case": sprintf("matrix:%s", [ch]), "msg": msg} if {
	some ch in {"A", "H"}
	cols := matrix[ch]
	full_rows(cols) != [3]
	msg := sprintf("D3: %q: full-width row(s) at %v, expected [3] — the crossbar disagrees with the rest of the font", [ch, full_rows(cols)])
}

# 'E' bars the top, middle and bottom; its middle bar shares row 3
defect contains {"case": "matrix:E", "msg": msg} if {
	cols := matrix.E
	rows_with(cols, 4) != [0, 3, 6]
	msg := sprintf("D3: 'E': barred rows %v, expected [0, 3, 6]", [rows_with(cols, 4)])
}

defect contains {"case": sprintf("matrix:%s", [ch]), "msg": msg} if {
	some ch in symmetric
	cols := matrix[ch]
	count(cols) > 0
	cols != array.reverse(cols)
	msg := sprintf("D3: %q is not left-right symmetric: %v", [ch, cols])
}

# no glyph but ' ' may be blank — a silently empty cell is how a missing glyph looks
defect contains {"case": sprintf("matrix:%s", [ch]), "msg": msg} if {
	some ch, cols in matrix
	ch != " "
	count([b | some b in cols; b != 0]) == 0
	msg := sprintf("D3: %q: every column is empty", [ch])
}

deny contains d.msg if some d in defect

admitted contains key if {
	some c in measured_cases
	key := sprintf("%s:%s", [c.kind, c.id])
	not denied_case[key]
}

denied_case contains d.case if some d in defect
