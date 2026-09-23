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

test_r1_refuses_an_absent_hook if {
	some msg in r.deny with input as object.union(good, {"hook_present": false})
	msg == "R1: the structural-query hook is not installed at scripts/hook_structural_query.py"
}
