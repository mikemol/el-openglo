package el.glb_test

import rego.v1

import data.el.glb

good := {"file": "el-seg7.glb", "present": true, "parse_error": null, "current": true,
	"want": ["a", "b", "c"], "nodes": ["a", "b", "c"], "flat": []}

test_stale_shader_denied if {
	inp := {"cases": [good], "extras": [{"file": "el-segment.glsl", "present": true, "current": false}]}
	"G6: el-segment.glsl is stale; run make_glb.py" in glb.deny with input as inp
}

test_overflow_denied if {
	"G7: glyph 7:x sets a bit past its format's node count" in glb.deny with input as {"cases": [good], "overflow": ["7:x"]}
}

test_order_mismatch_denied if {
	"G7: format 5x7: the glyph table's bit order is not its mesh's node order" in glb.deny with input as {"cases": [good], "order_mismatch": ["5x7"]}
}

test_shader_compile_failure_denied if {
	some m in glb.deny with input as {"cases": [good], "shader": {"ok": false, "why": "ERROR: 0:1"}}
	startswith(m, "G8:")
}

test_shader_unvalidated_is_skip if {
	inp := {"cases": [good], "shader": {"ok": null, "why": "glslangValidator not installed"}}
	count(glb.deny) == 0 with input as inp
	glb.skipped == {"glslangValidator not installed"} with input as inp
}

test_empty_population_denied if {
	count(glb.deny) == 1 with input as {}
}

test_good_mesh_admitted if {
	inp := {"cases": [good], "withheld": []}
	count(glb.deny) == 0 with input as inp
	glb.admitted == {"el-seg7.glb"} with input as inp
}

test_missing_file_denied if {
	"G1: el-seg7.glb: missing; run make_glb.py" in glb.deny with input as {"cases": [{"file": "el-seg7.glb", "present": false}]}
}

test_unparseable_denied if {
	inp := {"cases": [object.union(good, {"parse_error": "magic is not glTF", "nodes": []})]}
	"G2: el-seg7.glb: magic is not glTF" in glb.deny with input as inp
	count(glb.admitted) == 0 with input as inp
}

test_wrong_nodes_denied if {
	some m in glb.deny with input as {"cases": [object.union(good, {"nodes": ["a", "b"]})]}
	startswith(m, "G3: el-seg7.glb")
}

test_flat_node_denied if {
	"G4: el-seg7.glb: node b has no solid mesh" in glb.deny with input as {"cases": [object.union(good, {"flat": ["b"]})]}
}

test_stale_denied if {
	"G5: el-seg7.glb is stale; run make_glb.py" in glb.deny with input as {"cases": [object.union(good, {"current": false})]}
}
