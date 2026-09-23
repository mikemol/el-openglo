# METADATA
# title: "R0 — an empty routing table admits nothing"
# description: |
#   The measurement is `scripts/check_routes.py --json`: the rows the
#   structural-query hook reports from THIS repo's struct-tools skill. An empty
#   table is exactly the measured failure — the hook, symlinked into a repo with
#   no skill of its own, still fires and refuses but names no tool.
package el.routes

import rego.v1

import data.el.truth

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "R0: the hook reports an EMPTY routing table — it would refuse textual queries without naming the owning tool"
}

admitted contains c.row if {
	truth.py(input.hook_present)
	truth.py(input.skill_present)
	some c in input.cases
}

# METADATA
# title: "R1 — the hook is installed"
deny contains msg if {
	not input.hook_present
	msg := sprintf("R1: the structural-query hook is not installed at %v", [input.hook])
}

# METADATA
# title: "R2 — the routing table is LOCAL"
# description: |
#   The hook parses an absent file and fires with no tool named.
deny contains msg if {
	not input.skill_present
	msg := sprintf("R2: no local routing table at %v", [input.skill])
}
