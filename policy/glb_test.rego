package el.glb_test

import rego.v1

import data.el.glb

good := {"file": "el-seg7.glb", "present": true, "parse_error": null, "current": true,
	"want": ["a", "b", "c"], "nodes": ["a", "b", "c"], "flat": []}

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
