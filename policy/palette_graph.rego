# METADATA
# title: "G0 — an empty population is a broken search, not a clean graph"
# description: |
#   The measurement is `scripts/check_palette_graph.py --json`: palette_graph's
#   nodes (`cases`: emitted key + gate name), the token keys found by WALKING
#   make_schemes.GRID, the gate names cvd_gate's ENFORCED/SURFACED pairs use, the
#   edge count, and per class the authority's pairs beside cvd_gate's literals.
#   palette_graph claims to be the ONE place the constraint edges are named; a
#   partial mapping makes it a fourth namespace. Weakness: the emitted keys come
#   from the authored fallback tables, not a solver run (check_palette_chain
#   gates that the two agree); b1 (--b1) is a capacity, not a finding.
package el.palette_graph

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "G0: no nodes were measured; the search is broken, not the graph clean"
}

# the defect this check first shipped with: GRID read as a sequence when it is a
# dict, 0 emitted keys, every emitted-key comparison skipped, and a pass printed
deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	some part in ["emitted", "gate_names"]
	count(object.get(input, part, [])) == 0
	msg := sprintf("G0: %d nodes but 0 %s; the search is broken, not the graph clean", [count(input.cases), part])
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	object.get(input, "edges", 0) == 0
	msg := "G0: 0 edges; the search is broken, not the graph clean"
}

# METADATA
# title: "G1 — every node's emitted key appears in some variant"
deny contains msg if {
	some c in input.cases
	not c.id in {k | some k in input.emitted}
	msg := sprintf("G1: %s: emitted key %q appears in no variant", [c.id, c.id])
}

# METADATA
# title: "G2 — every node's gate name is in an ENFORCED/SURFACED pair, and every such name is claimed"
deny contains msg if {
	some c in input.cases
	c.gate != null
	not c.gate in {g | some g in input.gate_names}
	msg := sprintf("G2: %s: gate name %q is in no ENFORCED/SURFACED pair", [c.id, c.gate])
}

deny contains msg if {
	some g in input.gate_names
	not g in {c.gate | some c in input.cases; c.gate != null}
	msg := sprintf("G2: gate name %q is used by cvd_gate but claimed by no node", [g])
}

# METADATA
# title: "G3 — the authority's pairs are cvd_gate's pairs, per class"
deny contains msg if {
	some cls, ps in input.pairs
	some pr in ps.declared
	not pr in {q | some q in ps.authority}
	msg := sprintf("G3: %s: cvd_gate declares %v and the authority does not", [cls, pr])
}

deny contains msg if {
	some cls, ps in input.pairs
	some pr in ps.authority
	not pr in {q | some q in ps.declared}
	msg := sprintf("G3: %s: the authority declares %v and cvd_gate does not", [cls, pr])
}

admitted contains c.id if {
	some c in input.cases
	c.id in {k | some k in input.emitted}
	gate_ok(c)
}

gate_ok(c) if c.gate == null

gate_ok(c) if c.gate in {g | some g in input.gate_names}
