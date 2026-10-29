package el.render_race_test

import rego.v1

import data.el.render_race

good := {
	"min_lit": 20,
	"cases": [
		{"name": "control", "lit": 900},
		{"name": "held-default", "lit": 0},
		{"name": "held-settled", "lit": 900},
	],
}

test_absent_population_denied if {
	"R0: the forced render race was not measured" in render_race.deny with input as {}
}

test_forced_race_admitted if {
	count(render_race.deny) == 0 with input as good
}

test_settled_blank_denied if {
	some m in render_race.deny with input as object.union(good, {"cases": [{"name": "control", "lit": 900}, {"name": "held-default", "lit": 0}, {"name": "held-settled", "lit": 0}]})
	startswith(m, "R1:")
}

test_blind_control_denied if {
	some m in render_race.deny with input as object.union(good, {"cases": [{"name": "control", "lit": 3}, {"name": "held-default", "lit": 0}, {"name": "held-settled", "lit": 900}]})
	startswith(m, "R2:")
}

test_unforced_race_denied if {
	some m in render_race.deny with input as object.union(good, {"cases": [{"name": "control", "lit": 900}, {"name": "held-default", "lit": 900}, {"name": "held-settled", "lit": 900}]})
	startswith(m, "R3:")
}

test_unrendered_is_withheld_not_denied if {
	i := {"min_lit": 20, "cases": [], "withheld": ["control: the qml runner produced no image"]}
	count(render_race.deny) == 0 with input as i
	count(render_race.withheld) == 1 with input as i
}
