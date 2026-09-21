# A refusing and an admitting case per rule. The ring fixture is the
# arrive-and-expire-before-boundary scenario, verbatim from the harness.
package el.marquee_body_test

import data.el.marquee_body as mb
import rego.v1

parse_ok := {"body": "<b>hi</b>", "expected_text": "hi", "text": "hi", "expected_runs": [[0, 2, "bold"]], "runs": [[0, 2, "bold"]]}

join_ok := {"args": ["notify-send", "oh <b>hi</b>", ""], "expected_text": "notify-send: oh <b>hi</b>", "text": "notify-send: oh <b>hi</b>", "expected_runs": [], "runs": []}

ring_ok := {
	"label": "arrive-and-expire-before-boundary still scrolls once",
	"steps": [{"arrive": ["n1"], "live": [], "max": 12}],
	"expected": [{"ring": ["n1"], "queue": []}],
	"trace": [{"ring": ["n1"], "queue": [], "text": "n1#1"}],
}

clean := {"runner": true, "parse": [parse_ok], "join": [join_ok], "ring": [ring_ok]}

test_admits_clean if {
	count(mb.deny) == 0 with input as clean
	count(mb.withheld) == 0 with input as clean
}

test_m0_refuses_empty if {
	count(mb.deny) == 1 with input as {"runner": true, "parse": [], "join": [], "ring": []}
}

test_m1_refuses_wrong_text if {
	c := object.union(parse_ok, {"text": "<b>hi</b>"})
	some msg in mb.deny with input as object.union(clean, {"parse": [c]})
	startswith(msg, "M1:")
}

test_m1_refuses_lost_run if {
	c := object.union(parse_ok, {"runs": []})
	some msg in mb.deny with input as object.union(clean, {"parse": [c]})
	contains(msg, "styled runs")
}

test_m2_refuses_a_summary_parsed_as_markup if {
	c := object.union(join_ok, {"text": "notify-send: oh hi", "runs": [[16, 18, "bold"]]})
	some msg in mb.deny with input as object.union(clean, {"join": [c]})
	startswith(msg, "M2:")
}

test_m3_refuses_a_ring_that_differs if {
	r := object.union(ring_ok, {"trace": [{"ring": [], "queue": [], "text": ""}]})
	some msg in mb.deny with input as object.union(clean, {"ring": [r]})
	startswith(msg, "M3:")
}

test_m3_refuses_a_short_trace if {
	r := object.union(ring_ok, {"trace": []})
	some msg in mb.deny with input as object.union(clean, {"ring": [r]})
	contains(msg, "boundaries traced")
}

test_m4_refuses_an_arrival_never_rung if {
	# the EXPECTATION forgot the arrival too, so M3 is silent and only M4 speaks
	r := object.union(ring_ok, {"expected": [{"ring": [], "queue": []}], "trace": [{"ring": [], "queue": [], "text": ""}]})
	inp := object.union(clean, {"ring": [r]})
	some msg in mb.deny with input as inp
	startswith(msg, "M4:")
}

test_m4_admits_a_later_ring if {
	r := {
		"label": "waits",
		"steps": [{"arrive": ["n1"], "live": ["n1"], "max": 1}, {"arrive": [], "live": ["n1"], "max": 1}],
		"expected": [{"ring": [], "queue": ["n1"]}, {"ring": ["n1"], "queue": ["n1"]}],
		"trace": [{"ring": [], "queue": ["n1"], "text": ""}, {"ring": ["n1"], "queue": ["n1"], "text": "n1#1"}],
	}
	count([m | some m in mb.deny with input as object.union(clean, {"ring": [r]}); startswith(m, "M4:")]) == 0
}

test_withheld_without_runner if {
	inp := {"runner": false, "parse": [], "join": [], "ring": []}
	count(mb.deny) == 0 with input as inp
	count(mb.withheld) == 1 with input as inp
}
