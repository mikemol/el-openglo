package el.partial_test

import data.el.partial as p
import rego.v1

good := {"notes": "RECOVERY-NOTES.md", "notes_present": true, "cases": [
	{"file": "cvd_gate.py", "exists": true, "named": true},
	{"file": "make_deb.py", "exists": true, "named": true},
]}

test_admits_an_intact_record if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 2 with input as good
}

test_p0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "P0:")
}

test_p0_refuses_an_empty_roster if {
	some msg in p.deny with input as object.union(good, {"cases": []})
	startswith(msg, "P0:")
}

# the stale-record failure the docstring names: the roster still carries a file
# the tree no longer holds
test_p1_refuses_a_vanished_partial_file if {
	bad := object.union(good, {"cases": [good.cases[0], {"file": "make_deb.py", "exists": false, "named": true}]})
	some msg in p.deny with input as bad
	msg == "P1: make_deb.py is recorded as partial but absent from the tree"
}

test_p2_refuses_absent_notes if {
	bad := object.union(good, {"notes_present": false, "cases": [{"file": "cvd_gate.py", "exists": true, "named": false}]})
	some msg in p.deny with input as bad
	msg == "P2: RECOVERY-NOTES.md is absent — the provenance record is unreachable"
	count(p.admitted) == 0 with input as bad
}

test_p2_refuses_an_unnamed_partial_file if {
	bad := object.union(good, {"cases": [good.cases[0], {"file": "make_deb.py", "exists": true, "named": false}]})
	some msg in p.deny with input as bad
	msg == "P2: RECOVERY-NOTES.md does not mention make_deb.py"
}

# null is truthy to a bare Rego reference: a null notes_present must not count as
# "the notes are present" and fire the does-not-mention arm
test_null_notes_present_does_not_fire if {
	bad := object.union(good, {"notes_present": null, "cases": [good.cases[0], {"file": "make_deb.py", "exists": true, "named": false}]})
	not "P2: RECOVERY-NOTES.md does not mention make_deb.py" in p.deny with input as bad
}

# a null exists/named is not a measured yes: the file must not be admitted
test_null_exists_named_does_not_admit if {
	inp := object.union(good, {"cases": [good.cases[0], {"file": "make_deb.py", "exists": null, "named": null}]})
	not "make_deb.py" in p.admitted with input as inp
}
