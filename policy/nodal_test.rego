package el.nodal_test

import rego.v1

import data.el.nodal

row(v, moves, flat_min, flat_ser) := {"variant": v, "moves": moves, "flat_max_min": flat_min, "flat_series": flat_ser}

test_empty_population_denied if {
	count(nodal.deny) == 1 with input as {}
}

test_series_sees_every_move_admitted if {
	doc := {"cases": [row("EL-Azure", 143, 28, 0)]}
	count(nodal.deny) == 0 with input as doc
	count(nodal.admitted) == 1 with input as doc
}

test_series_blind_move_denied if {
	doc := {"cases": [row("EL-Azure", 143, 28, 3)]}
	some m in nodal.deny with input as doc
	startswith(m, "N2: EL-Azure")
}

test_empty_candidate_search_denied if {
	doc := {"cases": [row("EL-Azure", 0, 0, 0)]}
	some m in nodal.deny with input as doc
	startswith(m, "N0: EL-Azure")
}

test_max_min_blindness_alone_is_not_a_deny if {
	doc := {"cases": [row("EL-Azure", 143, 143, 0)]}
	count(nodal.deny) == 0 with input as doc
}
