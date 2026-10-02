package el.nodal_test

import rego.v1

import data.el.nodal

edge(id, m, r) := {"id": id, "variant": "EL-Azure", "u": "a", "v": "b", "margin": m, "r_eff": r}

test_empty_population_denied if {
	count(nodal.deny) == 1 with input as {}
}

test_clearing_and_holding_admitted if {
	doc := {"cases": [edge("x", 2.0, 1.4)], "withheld": []}
	count(nodal.deny) == 0 with input as doc
	count(nodal.admitted) == 1 with input as doc
}

test_near_through_others_denied if {
	doc := {"cases": [edge("x", 1.5, 0.6)], "withheld": []}
	some m in nodal.deny with input as doc
	startswith(m, "N1: x")
}

test_failing_alone_is_not_this_rules_business if {
	doc := {"cases": [edge("x", 0.7, 0.5)], "withheld": []}
	count(nodal.deny) == 0 with input as doc
}

test_unsolved_edge_denied if {
	doc := {"cases": [edge("x", 1.5, null)], "withheld": []}
	some m in nodal.deny with input as doc
	startswith(m, "N0: x")
}

test_unmeasurable_floor_withheld if {
	doc := {"cases": [edge("x", 2.0, 1.4)], "withheld": ["EL-Azure: fg~view: floor kind 'solve_lit/apca-argmax' has no margin form here"]}
	count(nodal.withheld) == 1 with input as doc
}
