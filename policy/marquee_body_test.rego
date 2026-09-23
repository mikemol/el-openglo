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

series_ok := {"label": "a ramp fills the rows", "args": [[0, 25, 50, 75, 100], 8, 0, 100], "expected": [0, 2, 4, 6, 8], "columns": [0, 2, 4, 6, 8]}

clean := {"runner": true, "parse": [parse_ok], "join": [join_ok], "ring": [ring_ok], "series": [series_ok]}

test_m6_refuses_a_boundary_off_its_stated_text if {
	acted := {"label": "actions", "steps": [{"arrive": ["n1"], "live": ["n1"], "max": 12, "text": "n1#1 [Open]"}],
		"expected": [{"ring": ["n1"], "queue": ["n1"]}], "trace": [{"ring": ["n1"], "queue": ["n1"], "text": "n1#1"}]}
	some msg in mb.deny with input as object.union(clean, {"ring": [acted]})
	startswith(msg, "M6:")
}

test_m6_admits_a_boundary_on_its_stated_text if {
	acted := {"label": "actions", "steps": [{"arrive": ["n1"], "live": ["n1"], "max": 12, "text": "n1#1 [Open]"}],
		"expected": [{"ring": ["n1"], "queue": ["n1"]}], "trace": [{"ring": ["n1"], "queue": ["n1"], "text": "n1#1 [Open]"}]}
	count([m | some m in mb.deny with input as object.union(clean, {"ring": [acted]}); startswith(m, "M6:")]) == 0
}

test_m7_refuses_a_boundary_off_its_stated_series if {
	job := {"label": "job", "steps": [{"arrive": ["j1"], "live": ["j1"], "max": 12, "series": {"j1": [10, 50]}}],
		"expected": [{"ring": ["j1"], "queue": ["j1"]}], "trace": [{"ring": ["j1"], "queue": ["j1"], "text": "j1#1", "series": {"j1": [10]}}]}
	some msg in mb.deny with input as object.union(clean, {"ring": [job]})
	startswith(msg, "M7:")
}

test_m7_admits_a_boundary_on_its_stated_series if {
	job := {"label": "job", "steps": [{"arrive": ["j1"], "live": ["j1"], "max": 12, "series": {"j1": [10, 50]}}],
		"expected": [{"ring": ["j1"], "queue": ["j1"]}], "trace": [{"ring": ["j1"], "queue": ["j1"], "text": "j1#1", "series": {"j1": [10, 50]}}]}
	count([m | some m in mb.deny with input as object.union(clean, {"ring": [job]}); startswith(m, "M7:")]) == 0
}

test_m5_refuses_drifted_columns if {
	some msg in mb.deny with input as object.union(clean, {"series": [object.union(series_ok, {"columns": [0, 2, 4, 6, 7]})]})
	startswith(msg, "M5:")
}

test_m5_refuses_no_series_cases if {
	some msg in mb.deny with input as object.union(clean, {"series": []})
	startswith(msg, "M5:")
}

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

# null is truthy to a bare Rego reference: a null runner has not run, so M0/M5 stay silent
test_null_runner_does_not_fire if {
	inp := {"runner": null, "parse": [], "join": [], "ring": [], "series": []}
	count([m | some m in mb.deny with input as inp; startswith(m, "M0:")]) == 0
	count([m | some m in mb.deny with input as inp; startswith(m, "M5:")]) == 0
}

# a null text/series is UNSTATED, not an expectation of null: M6/M7 stay silent
test_null_step_text_series_does_not_fire if {
	r := {"label": "unstated", "steps": [{"arrive": ["n1"], "live": [], "max": 12, "text": null, "series": null}],
		"expected": [{"ring": ["n1"], "queue": []}], "trace": [{"ring": ["n1"], "queue": [], "text": "n1#1", "series": {}}]}
	inp := object.union(clean, {"ring": [r]})
	count([m | some m in mb.deny with input as inp; startswith(m, "M6:")]) == 0
	count([m | some m in mb.deny with input as inp; startswith(m, "M7:")]) == 0
}

test_withheld_without_runner if {
	inp := {"runner": false, "parse": [], "join": [], "ring": []}
	count(mb.deny) == 0 with input as inp
	count(mb.withheld) == 1 with input as inp
}
