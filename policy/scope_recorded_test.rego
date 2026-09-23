package el.scope_recorded_test

import data.el.scope_recorded as s
import rego.v1

good := {"cases": [{"record": "RECOVERY-NOTES.md", "present": true,
	"evidence": [{"line": 12, "text": "retired because of a trademark concern; the rename"}]}]}

test_admits_a_recorded_decision if {
	count(s.deny) == 0 with input as good
	s.admitted == {"RECOVERY-NOTES.md"} with input as good
}

test_s0_refuses_an_absent_population if {
	some msg in s.deny with input as {}
	startswith(msg, "S0:")
}

test_s0_refuses_an_empty_population if {
	some msg in s.deny with input as {"cases": []}
	startswith(msg, "S0:")
}

test_s1_refuses_an_absent_record if {
	some msg in s.deny with input as {"cases": [{"record": "RECOVERY-NOTES.md", "present": false, "evidence": []}]}
	msg == "S1: RECOVERY-NOTES.md is absent; the rename decision has nowhere legible to live"
}

# the docstring's "delete the rationale and it goes red"
test_s2_refuses_a_record_without_the_rationale if {
	some msg in s.deny with input as {"cases": [{"record": "RECOVERY-NOTES.md", "present": true, "evidence": []}]}
	msg == "S2: RECOVERY-NOTES.md does not record WHY the prior mark was retired"
}

# null present is not held: no S2 (a record never read cannot lack its rationale)
test_null_present_does_not_fire if {
	inp := {"cases": [object.union(good.cases[0], {"present": null, "evidence": []})]}
	d := s.deny with input as inp
	every msg in d {
		not startswith(msg, "S2:")
	}
	not "RECOVERY-NOTES.md" in s.admitted with input as {"cases": [object.union(good.cases[0], {"present": null})]}
}
