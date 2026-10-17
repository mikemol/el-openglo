# A refusing and an admitting case per rule. The folded fixture is the measured W561 shape:
# a file staged beside the committed one, the plain amend committing it.
package el.post_commit_test

import data.el.post_commit as p
import rego.v1

clean := {"scenario": "staged-beside-the-committed-file", "amended": true, "folded": false, "still_staged": true}

good := {"hook": ".githooks/post-commit", "hook_present": true, "cases": [clean]}

test_admits_a_hook_that_leaves_the_index_alone if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	p.admitted == {"staged-beside-the-committed-file"} with input as good
}

test_p0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "P0:")
}

test_p0_refuses_an_empty_population_with_a_hook if {
	some msg in p.deny with input as {"hook_present": true, "cases": []}
	startswith(msg, "P0:")
}

test_an_absent_hook_is_withheld_not_denied if {
	inp := {"hook_present": false, "cases": []}
	count(p.deny) == 0 with input as inp
	some msg in p.withheld with input as inp
	startswith(msg, "P3: .githooks/post-commit is absent")
}

# the defect itself (W561): the plain amend folded the staged file into the tip
test_p1_refuses_a_folded_staged_file if {
	bad := object.union(good, {"cases": [object.union(clean, {"folded": true})]})
	some msg in p.deny with input as bad
	startswith(msg, "P1:")
	count(p.admitted) == 0 with input as bad
}

test_p2_refuses_a_staged_file_removed_from_the_index if {
	bad := object.union(good, {"cases": [object.union(clean, {"still_staged": false})]})
	some msg in p.deny with input as bad
	startswith(msg, "P2:")
}

# a hook that never amended proves nothing: withheld, not admitted, not denied
test_p3_withholds_a_hook_that_did_not_amend if {
	inp := object.union(good, {"cases": [object.union(clean, {"amended": false})]})
	count(p.deny) == 0 with input as inp
	some msg in p.withheld with input as inp
	contains(msg, "did not amend")
	count(p.admitted) == 0 with input as inp
}

# null is not a verdict: a null folded must not read as "not folded"
test_p3_withholds_an_unmeasured_fact if {
	inp := object.union(good, {"cases": [object.union(clean, {"folded": null})]})
	count(p.deny) == 0 with input as inp
	"P3: staged-beside-the-committed-file: folded was not measured" in p.withheld with input as inp
	count(p.admitted) == 0 with input as inp
}
