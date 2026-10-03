package el.hooks_test

import data.el.hooks as p
import rego.v1

good := {"cases": [
	{"hook": "hook_no_chaining.py", "present": true, "resolves": "/x/substrate/scripts/hook_no_chaining.py", "rc": 0, "tail": "PASS"},
	{"hook": "hook_structural_query.py", "present": true, "resolves": "/x/substrate/scripts/hook_structural_query.py", "rc": 0, "tail": "PASS"},
], "unwired": []}

# H4: an adopted hook settings.json does not run is a failure; none unwired admits; an
# unmeasured `unwired` is withheld, never read as "none"
test_h4_refuses_an_unwired_adopted_hook if {
	bad := object.union(good, {"unwired": ["mikemol-hook-pycheck"]})
	some msg in p.deny with input as bad
	msg == "H4: mikemol-hook-pycheck: adopted (PROBES declares it) but settings.json does not run it"
}

test_h4_admits_when_every_adopted_hook_is_wired if {
	count([m | some m in p.deny with input as good; startswith(m, "H4:")]) == 0
	count([m | some m in p.withheld with input as good; startswith(m, "H4:")]) == 0
}

test_h4_withholds_an_unmeasured_unwired if {
	inp := {"cases": good.cases}
	"H4: unwired was not measured" in p.withheld with input as inp
	count([m | some m in p.deny with input as inp; startswith(m, "H4:")]) == 0
}

test_admits_passing_hooks if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 2 with input as good
}

test_h0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "H0:")
}

# the failure the docstring names: settings.json runs a hook command that is not installed
test_h1_refuses_a_missing_hook_command if {
	bad := {"cases": [good.cases[0], {"hook": "mikemol-hook-structural-query", "present": false, "resolves": null, "rc": null, "tail": ""}]}
	some msg in p.deny with input as bad
	msg == "H1: mikemol-hook-structural-query: absent (not installed in .venv, or settings.json names a missing command)"
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
