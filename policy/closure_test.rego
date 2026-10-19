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

test_l5_refuses_an_insufficient_closure if {
	bad := object.union(good, {"witness": [{"script": "scripts/check_a.py", "arm1": "fail", "arm2": "none", "victim": null, "detail": "ModuleNotFoundError: gone"}]})
	some msg in p.deny with input as bad
	startswith(msg, "L5: scripts/check_a.py fails in a tree holding only its closure")
}

test_a_passing_witness_adds_no_denial if {
	ok := object.union(good, {"witness": [{"script": "scripts/check_a.py", "arm1": "pass", "arm2": "refused", "victim": "scripts/x.py", "detail": ""}]})
	count(p.deny) == 0 with input as ok
}

# not confirmed is not failed: an exempt stage and an unproven arm 2 are counted, never denied or admitted
test_exempt_and_unproven_are_withheld_not_judged if {
	w := object.union(good, {"witness": [
		{"script": "scripts/check_e.py", "arm1": "exempt", "arm2": "none", "victim": null, "detail": "needs a git index"},
		{"script": "scripts/check_u.py", "arm1": "pass", "arm2": "unproven", "victim": null, "detail": ""},
	]})
	count(p.deny) == 0 with input as w
	count([m | some m in p.withheld with input as w]) == 2
}

# a whole-gate stage that fails only on claims the harness cannot judge (no git, no untracked outputs) is
# sufficient EXCEPT those: withheld with the reason, never denied and never silently passed
test_a_known_failure_is_withheld_with_its_reason if {
	k := object.union(good, {"witness": [{"script": "worklist", "arm1": "known", "arm2": "none", "victim": null, "detail": "@EBUILD: needs a clone"}]})
	count(p.deny) == 0 with input as k
	"W: worklist passes its witness except the claims @EBUILD: needs a clone" in p.withheld with input as k
}

test_l6_refuses_a_dangling_load if {
	bad := object.union(good, {"tree": {"nodes": 3, "dangling": ["pytestspec -> pytestspec_gate"], "orphans": []}})
	some msg in p.deny with input as bad
	startswith(msg, "L6: pytestspec -> pytestspec_gate")
}

test_l7_refuses_an_orphan_node if {
	bad := object.union(good, {"tree": {"nodes": 3, "dangling": [], "orphans": ["pytestspec_lost"]}})
	some msg in p.deny with input as bad
	startswith(msg, "L7: closures_pytestspec_lost.bzl")
}

test_l8_refuses_a_listed_directory_with_no_tracked_file if {
	bad := object.union(good, {"tree": {"nodes": 3, "dangling": [], "orphans": [], "empty_dirs": ["pytestspec -> gone"]}})
	some msg in p.deny with input as bad
	startswith(msg, "L8: pytestspec -> gone")
}

test_a_tree_with_no_empty_listed_dir_adds_no_denial if {
	ok := object.union(good, {"tree": {"nodes": 3, "dangling": [], "orphans": [], "empty_dirs": []}})
	count(p.deny) == 0 with input as ok
}

test_a_clean_tree_adds_no_denial if {
	ok := object.union(good, {"tree": {"nodes": 8, "dangling": [], "orphans": []}})
	count(p.deny) == 0 with input as ok
}

test_l4_refuses_a_closure_for_a_gone_stage if {
	bad := object.union(good, {"stale": ["scripts/check_gone.py"]})
	some msg in p.deny with input as bad
	startswith(msg, "L4: closures.bzl carries a closure for scripts/check_gone.py")
}
