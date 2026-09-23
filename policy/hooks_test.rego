package el.hooks_test

import data.el.hooks as p
import rego.v1

good := {"cases": [
	{"hook": "hook_no_chaining.py", "present": true, "resolves": "/x/substrate/scripts/hook_no_chaining.py", "rc": 0, "tail": "PASS"},
	{"hook": "hook_structural_query.py", "present": true, "resolves": "/x/substrate/scripts/hook_structural_query.py", "rc": 0, "tail": "PASS"},
]}

test_admits_passing_hooks if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 2 with input as good
}

test_h0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "H0:")
}

# the failure the docstring names: the symlink dangles because upstream moved
test_h1_refuses_a_dangling_symlink if {
	bad := {"cases": [good.cases[0], {"hook": "hook_structural_query.py", "present": false, "resolves": null, "rc": null, "tail": ""}]}
	some msg in p.deny with input as bad
	msg == "H1: hook_structural_query.py: absent (dangling symlink, or not installed yet)"
	count(p.admitted) == 1 with input as bad
}

test_h2_refuses_a_failing_selftest if {
	bad := {"cases": [{"hook": "hook_no_chaining.py", "present": true, "resolves": "/x", "rc": 1, "tail": "selftest: FAIL"}]}
	some msg in p.deny with input as bad
	msg == "H2: hook_no_chaining.py: selftest exited 1: selftest: FAIL"
}

# null is truthy to a bare Rego reference: an unstated `present` must not arm H2 or admit
test_null_present_does_not_fire if {
	failing := {"cases": [{"hook": "hook_no_chaining.py", "present": null, "resolves": "/x", "rc": 1, "tail": "selftest: FAIL"}]}
	count([m | some m in p.deny with input as failing; startswith(m, "H2:")]) == 0
	passing := {"cases": [object.union(good.cases[0], {"present": null})]}
	count(p.admitted) == 0 with input as passing
}

# exactly-once: a case whose judged fields are all null is withheld, never judged
test_all_null_case_withheld_only if {
	inp := {"cases": [{"hook": "hook_no_chaining.py", "present": null, "resolves": null, "rc": null, "tail": null}, good.cases[1]]}
	w := p.withheld with input as inp
	"H3: hook_no_chaining.py: present was not measured" in w
	d := p.deny with input as inp
	count([x | some x in d; contains(x, "hook_no_chaining.py")]) == 0
	not "hook_no_chaining.py" in p.admitted with input as inp
}

# N1 (H1 `not c.present`): a null present is withheld, not silently nothing
test_null_present_is_withheld if {
	inp := {"cases": [{"hook": "hook_no_chaining.py", "present": null, "resolves": "/x", "rc": 0, "tail": "PASS"}]}
	w := p.withheld with input as inp
	"H3: hook_no_chaining.py: present was not measured" in w
}

# a present hook whose rc is null could not say whether its selftest passed
test_present_null_rc_withheld if {
	inp := {"cases": [{"hook": "hook_no_chaining.py", "present": true, "resolves": "/x", "rc": null, "tail": ""}]}
	w := p.withheld with input as inp
	"H3: hook_no_chaining.py: rc was not measured" in w
	count(p.deny) == 0 with input as inp
}
