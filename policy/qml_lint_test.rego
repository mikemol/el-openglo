# Every rule has a REFUSING case and an ADMITTING case (the falsifiability
# discipline, in the standard form: `opa test policy/`). The refusing fixture
# for Q2 is the marquee's own binding, verbatim from the live defect.
package el.qml_lint_test

import data.el.qml_lint
import rego.v1

clean := {"qmllint": true, "documents": [
	{"id": "marquee-main.qml", "lint": [], "bound_running": []},
	{"id": "clock-main.qml", "lint": [], "bound_running": []},
]}

test_admits_clean if {
	count(qml_lint.deny) == 0 with input as clean
	count(qml_lint.withheld) == 0 with input as clean
}

test_q0_refuses_empty_population if {
	count(qml_lint.deny) == 1 with input as {"qmllint": true, "documents": []}
}

# `count(input.documents)` is undefined on {} and an undefined body admits:
# the Q0 rule reads object.get, and this is the case that shows it
test_q0_refuses_an_absent_population if {
	some msg in qml_lint.deny with input as {}
	startswith(msg, "Q0:")
}

test_admitted_counts_the_clean_documents if {
	count(qml_lint.admitted) == 2 with input as clean
}

# a withheld document beside admitted ones is a SKIP, not "nothing judged"
test_withheld_beside_admitted_is_a_skip if {
	inp := {"qmllint": true, "documents": [
		{"id": "marquee-main.qml", "withheld": "a pinned host file is absent"},
		{"id": "clock-main.qml", "lint": [], "bound_running": []},
	]}
	qml_lint.admitted == {"clock-main.qml"} with input as inp
}

test_a_refused_document_is_not_admitted if {
	inp := {"qmllint": true, "documents": [{"id": "marquee-main.qml", "lint": [], "bound_running": [{"animation": "NumberAnimation", "loops": "1"}]}]}
	count(qml_lint.admitted) == 0 with input as inp
}

test_q1_refuses_a_lint_error if {
	inp := {"qmllint": true, "documents": [{"id": "broken.qml", "lint": ["broken.qml:2:14: [syntax] Expected token"], "bound_running": []}]}
	some msg in qml_lint.deny with input as inp
	startswith(msg, "Q1: broken.qml")
}

test_q2_refuses_the_marquee_binding if {
	inp := {"qmllint": true, "documents": [{"id": "marquee-main.qml", "lint": [], "bound_running": [{"animation": "NumberAnimation", "loops": "1"}]}]}
	some msg in qml_lint.deny with input as inp
	startswith(msg, "Q2: marquee-main.qml: NumberAnimation with loops 1")
}

test_q2_admits_a_started_animation if {
	count(qml_lint.deny) == 0 with input as clean
}

test_withheld_is_not_deny if {
	inp := {"qmllint": true, "documents": [
		{"id": "marquee-main.qml", "withheld": "a pinned host file is absent"},
		{"id": "clock-main.qml", "lint": [], "bound_running": []},
	]}
	count(qml_lint.deny) == 0 with input as inp
	count(qml_lint.withheld) == 1 with input as inp
}

test_withheld_without_qmllint if {
	inp := {"qmllint": false, "documents": [{"id": "clock-main.qml", "lint": [], "bound_running": []}]}
	count(qml_lint.deny) == 0 with input as inp
	count(qml_lint.withheld) == 1 with input as inp
}
