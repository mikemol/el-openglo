package el.closure_test

import data.el.closure as p
import rego.v1

good := {"cases": [
	{"script": "scripts/check_a.py", "has_closure": true, "files": 12, "self_listed": true, "untracked": []},
	{"script": "scripts/check_b.py", "has_closure": true, "files": 3, "self_listed": true, "untracked": []},
], "stale": []}

test_admits_declared_closures if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 2 with input as good
}

test_l0_refuses_an_empty_population if {
	some msg in p.deny with input as {"cases": [], "stale": []}
	startswith(msg, "L0:")
}

test_l0_absent_population_is_empty if {
	some msg in p.deny with input as {}
	startswith(msg, "L0:")
}

test_l1_refuses_a_stage_with_no_closure if {
	bad := object.union(good, {"cases": [{"script": "scripts/check_new.py", "has_closure": false, "files": 0, "self_listed": false, "untracked": []}]})
	some msg in p.deny with input as bad
	startswith(msg, "L1: scripts/check_new.py has no closure")
	count(p.admitted) == 0 with input as bad
}

test_l2_refuses_a_closure_missing_its_own_script if {
	bad := object.union(good, {"cases": [{"script": "scripts/check_a.py", "has_closure": true, "files": 5, "self_listed": false, "untracked": []}]})
	some msg in p.deny with input as bad
	startswith(msg, "L2:")
}

test_l3_refuses_an_untracked_listed_file if {
	bad := object.union(good, {"cases": [{"script": "scripts/check_a.py", "has_closure": true, "files": 5, "self_listed": true, "untracked": [".palette-cache.json"]}]})
	some msg in p.deny with input as bad
	startswith(msg, "L3: the closure of scripts/check_a.py lists .palette-cache.json")
}

test_l4_refuses_a_closure_for_a_gone_stage if {
	bad := object.union(good, {"stale": ["scripts/check_gone.py"]})
	some msg in p.deny with input as bad
	startswith(msg, "L4: closures.bzl carries a closure for scripts/check_gone.py")
}
