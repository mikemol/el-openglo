package el.metrics_test

import rego.v1

import data.el.metrics

good := [
	{"scenario": "tool-missing", "face": "endpoint-unavailable", "text": "ENDPOINT UNAVAILABLE"},
	{"scenario": "tool-refused", "face": "endpoint-unavailable", "text": "ENDPOINT UNAVAILABLE"},
	{"scenario": "tool-unreadable", "face": "endpoint-unavailable", "text": "ENDPOINT UNAVAILABLE"},
	{"scenario": "query-failed", "face": "unreachable", "text": "UNREACHABLE"},
	{"scenario": "query-ok", "face": "values", "text": "CPU 12%"},
]

test_empty_population_denied if {
	count(metrics.deny) == 1 with input as {}
}

test_every_scenario_correct_admitted if {
	count(metrics.deny) == 0 with input as {"cases": good}
	count(metrics.admitted) == 5 with input as {"cases": good}
}

test_unmeasured_scenario_denied if {
	some m in metrics.deny with input as {"cases": array.slice(good, 0, 4)}
	contains(m, "query-ok")
}

test_wrong_face_denied if {
	bad := array.concat(array.slice(good, 0, 3), [
		{"scenario": "query-failed", "face": "values", "text": "CPU 0%"},
		good[4],
	])
	some m in metrics.deny with input as {"cases": bad}
	startswith(m, "M1: query-failed")
}

test_blank_denied if {
	bad := array.concat(array.slice(good, 0, 4), [{"scenario": "query-ok", "face": "values", "text": ""}])
	some m in metrics.deny with input as {"cases": bad}
	startswith(m, "M2: query-ok")
}

test_missing_text_denied if {
	bad := array.concat(array.slice(good, 0, 4), [{"scenario": "query-ok", "face": "values"}])
	some m in metrics.deny with input as {"cases": bad}
	startswith(m, "M2: query-ok")
}

test_address_literal_denied if {
	some m in metrics.deny with input as {"cases": good, "address_literals": ["vmsingle.example:8428"]}
	startswith(m, "M3:")
}
