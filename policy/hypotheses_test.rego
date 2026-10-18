package el.hypotheses_test

import data.el.hypotheses as p
import rego.v1

closed := {
	"id": "W200-frame-18-tear",
	"status": "closed",
	"question": "what a capture series contains at a run boundary",
	"rule": "S: a capture series is exactly one run, its last frame the run end",
	"structure": "captureRuns marks the run end on every path",
	"boundary": [],
}

test_admits_a_closed_hypothesis if {
	count(p.deny) == 0 with input as {"hypotheses": [closed]}
	count(p.withheld) == 0 with input as {"hypotheses": [closed]}
	p.admitted == {"W200-frame-18-tear"} with input as {"hypotheses": [closed]}
}

test_h0_refuses_an_absent_population if {
	"H0: no hypothesis was read; the register is unread, not settled" in p.deny with input as {}
}

test_h1_refuses_a_hypothesis_with_no_question if {
	h := object.union(closed, {"question": ""})
	"H1: W200-frame-18-tear states no question; a hypothesis with none marks no ambiguity" in p.deny with input as {"hypotheses": [h]}
}

# the 2026-10-01 failure: two hypotheses stated and falsified in chat and ledger prose only
test_h2_refuses_a_close_on_a_verdict_alone if {
	h := object.union(closed, {"rule": ""})
	"H2: W200-frame-18-tear is closed on a verdict alone; the model gained no rule to decide it" in p.deny with input as {"hypotheses": [h]}
	count(p.admitted) == 0 with input as {"hypotheses": [h]}
}

test_h3_refuses_a_rule_nothing_can_check if {
	h := object.remove(closed, ["structure"])
	"H3: W200-frame-18-tear is closed with no implementation structure that makes its rule checkable" in p.deny with input as {"hypotheses": [h]}
}

test_h4_refuses_a_close_with_an_open_edge if {
	h := object.union(closed, {"boundary": ["a series that contains no complete run"]})
	some m in p.deny with input as {"hypotheses": [h]}
	startswith(m, "H4: W200-frame-18-tear is closed but its new rule has an open edge")
}

# an open hypothesis is withheld, a SKIP beside the admitted one
test_h5_withholds_an_open_hypothesis if {
	open := {"id": "W201-x", "status": "open", "question": "an unsettled thing"}
	inp := {"hypotheses": [closed, open]}
	"H5: W201-x is still open; the model and the implementation are not both refined at its boundary" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
	p.admitted == {"W200-frame-18-tear"} with input as inp
}
