# METADATA
# title: "G0 — no mesh measured admits nothing"
# description: |
#   The measurement is `scripts/check_glb.py --json`: per mesh make_glb declares
#   (7/16/22-segment and the 5x7 matrix), whether catalog/engines/<file> exists and
#   parses as GLB, its node names against the names its format demands, the nodes
#   whose mesh is empty or flat, and whether it equals a fresh emission. W152.
package el.glb

import rego.v1

deny contains "G0: no mesh was measured; the roster is empty, not the meshes complete" if {
	count(object.get(input, "cases", [])) == 0
	count(object.get(input, "withheld", [])) == 0
}

# METADATA
# title: "G1 — every declared mesh file exists"
deny contains msg if {
	some c in input.cases
	c.present == false
	msg := sprintf("G1: %s: missing; run make_glb.py", [c.file])
}

# METADATA
# title: "G2 — the file is a GLB container (magic, version 2, length, JSON + BIN chunks)"
deny contains msg if {
	some c in input.cases
	c.present == true
	is_string(c.parse_error)
	msg := sprintf("G2: %s: %s", [c.file, c.parse_error])
}

# METADATA
# title: "G3 — the nodes are exactly the format's named segments (or the matrix grid)"
deny contains msg if {
	some c in input.cases
	c.present == true
	c.parse_error == null
	c.nodes != c.want
	msg := sprintf("G3: %s: nodes %v, want %v", [c.file, c.nodes, c.want])
}

# METADATA
# title: "G4 — every node carries a solid mesh (triangles, extent on all three axes)"
deny contains msg if {
	some c in input.cases
	c.present == true
	some n in c.flat
	msg := sprintf("G4: %s: node %s has no solid mesh", [c.file, n])
}

# METADATA
# title: "G5 — the committed file is current (equals a fresh emission)"
deny contains msg if {
	some c in input.cases
	c.present == true
	c.current == false
	msg := sprintf("G5: %s is stale; run make_glb.py", [c.file])
}

withheld contains msg if {
	some msg in object.get(input, "withheld", [])
}

admitted contains c.file if {
	some c in input.cases
	c.present == true
	c.parse_error == null
	c.nodes == c.want
	count(c.flat) == 0
	c.current == true
}
