package el.solver_roots_test

import rego.v1

import data.el.solver_roots

case(side, reachable, candidate, n) := {
	"id": sprintf("EL-Azure/selection/neg/%s", [side]), "variant": "EL-Azure", "field": "selection",
	"slot": "neg", "side": side, "reachable": reachable, "candidate": candidate, "n_candidates": n,
}

test_empty_population_denied if {
	count(solver_roots.deny) == 1 with input as {}
}

test_both_roots_covered_admitted if {
	doc := {"floor": 4.6, "cases": [case("lighter", 7.0, 5.0, 3), case("darker", 6.0, 4.8, 2)]}
	count(solver_roots.deny) == 0 with input as doc
	count(solver_roots.admitted) == 2 with input as doc
}

test_uncovered_root_denied if {
	doc := {"floor": 4.6, "cases": [case("lighter", 7.0, 5.0, 3), case("darker", 6.0, null, 0)]}
	some m in solver_roots.deny with input as doc
	startswith(m, "R1: EL-Azure/selection/neg/darker")
}

test_candidates_below_floor_on_a_reachable_root_denied if {
	doc := {"floor": 4.6, "cases": [case("lighter", 7.0, 3.3, 4)]}
	count(solver_roots.deny) == 1 with input as doc
}

test_unreachable_side_is_not_a_root if {
	doc := {"floor": 4.6, "cases": [case("darker", 2.1, null, 0)]}
	count(solver_roots.deny) == 0 with input as doc
	count(solver_roots.admitted) == 1 with input as doc
}
