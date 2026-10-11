package el.census_test

import data.el.census as p
import rego.v1

good := {"checked": true, "withheld": null, "tracked": 3, "cases": [
	{"path": "a.py", "status": "named", "reason": ""},
	{"path": "b.py", "status": "named", "reason": ""},
	{"path": "c.png", "status": "exempt", "reason": "generated sample, read by no stage"},
]}

test_admits_a_fully_named_tree if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 3 with input as good
}

test_n0_refuses_an_empty_population if {
	some msg in p.deny with input as {"checked": true, "cases": [], "tracked": 0}
	startswith(msg, "N0:")
}

test_n0_absent_population_is_empty if {
	some msg in p.deny with input as {}
	startswith(msg, "N0:")
}

# the rule itself: a tracked file nobody named fails the gate
test_n1_refuses_a_tracked_file_no_stage_names if {
	bad := object.union(good, {"cases": [{"path": "x.py", "status": "unnamed", "reason": ""}]})
	some msg in p.deny with input as bad
	startswith(msg, "N1: x.py is tracked and no stage names it")
	not "x.py" in p.admitted with input as bad
}

test_n2_refuses_an_exemption_without_a_reason if {
	bad := object.union(good, {"cases": [{"path": "x.py", "status": "unreasoned", "reason": ""}]})
	some msg in p.deny with input as bad
	startswith(msg, "N2: x.py")
}

test_n3_refuses_a_stale_exemption if {
	bad := object.union(good, {"cases": [{"path": "x.py", "status": "stale", "reason": "old"}]})
	some msg in p.deny with input as bad
	startswith(msg, "N3: x.py is exempt (old)")
}

test_n4_refuses_an_exemption_for_an_untracked_file if {
	bad := object.union(good, {"cases": [{"path": "zz.py", "status": "gone", "reason": "was"}]})
	some msg in p.deny with input as bad
	startswith(msg, "N4: zz.py")
}

# outside bazel there is nothing to compare against: withheld, never read as admitted or denied
test_not_under_bazel_is_withheld_not_judged if {
	off := {"checked": false, "cases": [], "tracked": 662, "withheld": "no runfiles tree"}
	"W: no runfiles tree" in p.withheld with input as off
	count(p.deny) == 0 with input as off
	count(p.admitted) == 0 with input as off
}
