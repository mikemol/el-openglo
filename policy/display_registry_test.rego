package el.display_registry_test

import data.el.display_registry as p
import rego.v1

rt := {"parsed": true, "error": null, "keys": [
	{"key": "font5x7", "emitted": true, "registry": true, "equal": true},
	{"key": "segGeom", "emitted": true, "registry": true, "equal": true},
]}

good := {"roundtrip": rt, "cases": [
	{"kind": "stroke", "id": "a1", "in_substrate": true},
	{"kind": "format", "id": "7", "glyphs": [{"ch": "1", "emitted": ["b", "c"], "substrate": ["b", "c"]}]},
	{"kind": "matrix", "id": "A", "cols": [126, 9, 9, 9, 126]},
	{"kind": "matrix", "id": "H", "cols": [127, 8, 8, 8, 127]},
	{"kind": "matrix", "id": "E", "cols": [127, 73, 73, 73, 65]},
	{"kind": "matrix", "id": "0", "cols": [62, 81, 73, 69, 62]},
	{"kind": "matrix", "id": " ", "cols": [0, 0, 0, 0, 0]},
	{"kind": "display", "id": "7"},
]}

with_case(i, c) := {"roundtrip": rt, "cases": array.concat(array.slice(good.cases, 0, i), array.concat([c], array.slice(good.cases, i + 1, count(good.cases))))}

test_admits_a_faithful_registry if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 8 with input as good
}

test_d0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "D0:")
}

test_d0_refuses_an_empty_kind if {
	bad := {"roundtrip": rt, "cases": [c | some c in good.cases; c.kind != "display"]}
	some msg in p.deny with input as bad
	msg == "D0: the registry has no display entries — an empty population, not an agreeing registry"
}

# ⚑ THE EXACT BYTES THAT SHIPPED: 'A' = 0x7e,0x11,0x11,0x11,0x7e, crossbar on
# row 4 and a flat apex, green on every check because it round-tripped
test_d3_refuses_the_a_that_shipped if {
	bad := with_case(2, {"kind": "matrix", "id": "A", "cols": [126, 17, 17, 17, 126]})
	some msg in p.deny with input as bad
	startswith(msg, "D3: \"A\": full-width row(s) at [4], expected [3]")
	not p.admitted["matrix:A"] with input as bad
	count(p.admitted) == 7 with input as bad
}

# the selftest's asymmetric 'H' (0x7f,0x08,0x08,0x08,0x3f)
test_d3_refuses_an_asymmetric_symmetric_letter if {
	bad := with_case(3, {"kind": "matrix", "id": "H", "cols": [127, 8, 8, 8, 63]})
	some msg in p.deny with input as bad
	startswith(msg, "D3: \"H\" is not left-right symmetric")
}

# the selftest's 'Z' with a column byte 0xff: it lights a row the cell lacks
test_d3_refuses_a_column_past_the_cell if {
	bad := {"roundtrip": rt, "cases": array.concat(good.cases, [{"kind": "matrix", "id": "Z", "cols": [255, 81, 73, 69, 67]}])}
	some msg in p.deny with input as bad
	msg == "D3: \"Z\" column 0 = 255 lights a row past 7"
}

test_d3_refuses_a_blank_glyph_and_a_missing_crossbar_letter if {
	bad := with_case(3, {"kind": "matrix", "id": "Q", "cols": [0, 0, 0, 0, 0]})
	some m1 in p.deny with input as bad
	m1 == "D3: \"Q\": every column is empty"
	some m2 in p.deny with input as bad
	m2 == "D3: \"H\": absent from the font"
}

test_d3_refuses_a_misplaced_e_bar if {
	bad := with_case(4, {"kind": "matrix", "id": "E", "cols": [127, 81, 81, 81, 65]})
	some msg in p.deny with input as bad
	startswith(msg, "D3: 'E': barred rows [0, 4, 6]")
}

# '0' is deliberately asymmetric (its slash) and is admitted
test_d3_admits_the_slashed_zero if {
	p.admitted["matrix:0"] with input as good
}

# the selftest's dropped and mangled serialisations
test_d1_refuses_a_dropped_table if {
	bad := object.union(good, {"roundtrip": {"parsed": true, "error": null, "keys": [{"key": "font5x7", "emitted": false, "registry": true, "equal": false}]}})
	some msg in p.deny with input as bad
	msg == "D1: font5x7: emitted registry is missing it"
}

test_d1_refuses_a_mangled_table if {
	bad := object.union(good, {"roundtrip": {"parsed": true, "error": null, "keys": [{"key": "segGeom", "emitted": true, "registry": true, "equal": false}]}})
	some msg in p.deny with input as bad
	msg == "D1: segGeom: emitted value differs from registry()"
}

test_d1_refuses_an_invented_table_and_an_unparseable_emission if {
	bad := object.union(good, {"roundtrip": {"parsed": false, "error": "Expecting value", "keys": [{"key": "zz", "emitted": true, "registry": false, "equal": false}]}})
	some m1 in p.deny with input as bad
	m1 == "D1: zz: emitted registry invents it"
	some m2 in p.deny with input as bad
	m2 == "D1: as_qml_js is not parseable: Expecting value"
}

# null emitted / registry are not "present": D1 neither invents nor differs
test_null_emitted_registry_does_not_fire if {
	bad := object.union(good, {"roundtrip": {"parsed": true, "error": null, "keys": [
		{"key": "zz", "emitted": null, "registry": false, "equal": false},
		{"key": "segGeom", "emitted": true, "registry": null, "equal": false},
	]}})
	d := p.deny with input as bad
	every msg in d { not contains(msg, "invents it"); not contains(msg, "differs from registry") }
}

# the selftest's substrate disagreement: a glyph rewritten to ["zz"]
test_d2_refuses_a_substrate_disagreement if {
	bad := with_case(1, {"kind": "format", "id": "7", "glyphs": [{"ch": "1", "emitted": ["zz"], "substrate": ["b", "c"]}]})
	some msg in p.deny with input as bad
	startswith(msg, "D2: segGlyphs[7][\"1\"] = [\"zz\"]")
	not p.admitted["format:7"] with input as bad
}

test_d2_refuses_a_glyph_in_no_table_and_an_unknown_stroke if {
	bad := {"roundtrip": rt, "cases": array.concat(
		[{"kind": "stroke", "id": "q9", "in_substrate": false}, {"kind": "format", "id": "22", "glyphs": [{"ch": "☃", "emitted": [], "substrate": null}]}],
		good.cases,
	)}
	some m1 in p.deny with input as bad
	m1 == "D2: segGeom names \"q9\", which GEOM22 does not define"
	some m2 in p.deny with input as bad
	m2 == "D2: segGlyphs[22][\"☃\"] is in no substrate table"
}
