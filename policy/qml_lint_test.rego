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

# null is truthy to a bare Rego reference: a null withheld is not a withholding
test_null_withheld_does_not_fire if {
	inp := {"qmllint": true, "documents": [{"id": "clock-main.qml", "lint": [], "bound_running": [], "withheld": null}]}
	count(qml_lint.withheld) == 0 with input as inp
}

test_all_null_case_withheld_only if {
	inp := {"qmllint": true, "documents": [
		{"id": "clock-main.qml", "lint": [], "bound_running": []},
		{"id": "marquee-main.qml", "withheld": null, "lint": null, "bound_running": null},
	]}
	w := qml_lint.withheld with input as inp
	w == {"marquee-main.qml: lint was not measured", "marquee-main.qml: bound_running was not measured"}
	qml_lint.admitted == {"clock-main.qml"} with input as inp
	count(qml_lint.deny) == 0 with input as inp
}

# N1 fix (line 71): HEAD's `not input.qmllint` read a null qmllint as installed
test_null_qmllint_is_withheld if {
	inp := object.union(clean, {"qmllint": null})
	"qmllint was not measured; Q1 cannot say whether it ran" in qml_lint.withheld with input as inp
}

# N1 fix (line 64): HEAD's `not doc.withheld` read a null reason as a withholding,
# so a clean rendered document was never admitted — and not withheld either
test_null_withheld_document_is_admitted if {
	inp := {"qmllint": true, "documents": [{"id": "clock-main.qml", "lint": [], "bound_running": [], "withheld": null}]}
	qml_lint.admitted == {"clock-main.qml"} with input as inp
}

test_withheld_without_qmllint if {
	inp := {"qmllint": false, "documents": [{"id": "clock-main.qml", "lint": [], "bound_running": []}]}
	count(qml_lint.deny) == 0 with input as inp
	count(qml_lint.withheld) == 1 with input as inp
}
