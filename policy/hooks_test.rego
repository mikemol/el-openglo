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
