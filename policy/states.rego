# METADATA
# title: "S0 — no variants measured admits nothing"
# description: |
#   The measurement is `scripts/check_states.py --json`: per variant in
#   make_schemes.GRID, the three decoration states (focus, hover, sel_bg), their
#   pairwise q under cvd_gate._worst_normalized, and each state's WCAG ratio on
#   its ground (`view`). relations.md §4b, W10.
#   Weakness: q is judged on flat swatches; a 2px ring beside a field is judged
#   by the same number as two fields.
package el.states

import rego.v1

q_floor := 1.0

ground_floor := 3.0 # AA-large: a ring or field must be findable on its ground

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "S0: no variants were measured; the grid is empty, not the states distinct"
}

# METADATA
# title: "S1 — the states are pairwise distinguishable (q >= 1)"
deny contains msg if {
	some c in input.cases
	some pr in c.pairs
	pr.q < q_floor
	msg := sprintf("S1: %s: %s/%s q=%v < %v", [c.id, pr.a, pr.b, round(pr.q * 100) / 100, q_floor])
}

# METADATA
# title: "S2 — each state clears its ground (WCAG >= 3)"
deny contains msg if {
	some c in input.cases
	some g in c.grounds
	g.ratio < ground_floor
	msg := sprintf("S2: %s: %s on ground %v < %v", [c.id, g.state, round(g.ratio * 100) / 100, ground_floor])
}

admitted contains c.id if {
	some c in input.cases
	every pr in c.pairs { pr.q >= q_floor }
	every g in c.grounds { g.ratio >= ground_floor }
}
