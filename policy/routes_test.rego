package el.routes_test

import data.el.routes as r
import rego.v1

hook := "scripts/hook_structural_query.py"

skill := ".claude/skills/struct-tools/SKILL.md"

good := {"hook": hook, "hook_present": true, "skill": skill, "skill_present": true,
	"cases": [{"row": ".py -> ../substrate/scratch/pycodemod.py"}]}

test_admits_a_populated_local_table if {
	count(r.deny) == 0 with input as good
}

test_r0_refuses_an_absent_population if {
	some msg in r.deny with input as {}
	startswith(msg, "R0:")
}

# the measured failure: hook symlinked in, no local skill — the table comes back empty
test_r0_r2_refuse_the_symlinked_hook_without_a_skill if {
	bad := object.union(good, {"skill_present": false, "cases": []})
	some m0 in r.deny with input as bad
	startswith(m0, "R0:")
	some m2 in r.deny with input as bad
	m2 == "R2: no local routing table at .claude/skills/struct-tools/SKILL.md"
}

# null is truthy to a bare Rego reference: a null presence is not presence
test_null_hook_skill_present_does_not_admit if {
	count(r.admitted) == 0 with input as object.union(good, {"hook_present": null})
	count(r.admitted) == 0 with input as object.union(good, {"skill_present": null})
}

# N1 fixes (R1 `not input.hook_present`, R2 `not input.skill_present`): null is
# not measured — withheld, never "not installed"
test_null_hook_present_withheld_not_denied if {
	inp := object.union(good, {"hook_present": null})
	d := r.deny with input as inp
	every msg in d {
		not startswith(msg, "R1:")
	}
	r.withheld == {"R3: hook_present was not measured"} with input as inp
}

test_null_skill_present_withheld_not_denied if {
	inp := object.union(good, {"skill_present": null})
	d := r.deny with input as inp
	every msg in d {
		not startswith(msg, "R2:")
	}
	r.withheld == {"R3: skill_present was not measured"} with input as inp
}

test_all_null_case_withheld_only if {
	inp := object.union(good, {"cases": [{"row": null}]})
	r.withheld == {"R3: row 0: row was not measured"} with input as inp
	count(r.admitted) == 0 with input as inp
	count(r.deny) == 0 with input as inp
}

test_r2_refuses_an_absent_skill if {
	some msg in r.deny with input as object.union(good, {"skill_present": false})
	startswith(msg, "R2:")
}

test_r1_refuses_an_absent_hook if {
	some msg in r.deny with input as object.union(good, {"hook_present": false})
	msg == "R1: the structural-query hook is not installed at scripts/hook_structural_query.py"
}
