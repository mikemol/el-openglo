# METADATA
# title: "R0 — an empty routing table admits nothing"
# description: |
#   The measurement is `scripts/check_routes.py --json`: the rows the
#   structural-query hook reports from THIS repo's struct-tools skill. An empty
#   table is exactly the measured failure — the hook, symlinked into a repo with
#   no skill of its own, still fires and refuses but names no tool.
#
#   ⚑ EVERY ROW LANDS IN EXACTLY ONE OF withheld / deny / admitted.
#   `hook_present` and `skill_present` are booleans the measurement ALWAYS
#   emits; null or absent is "could not say" — R3 withholds it and neither R1/R2
#   nor the admit judges it. A row with no text is withheld the same way.
# custom:
#   family: gate
package el.routes

import rego.v1

import data.el.truth

flags := ["hook_present", "skill_present"]

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "R0: the hook reports an EMPTY routing table — it would refuse textual queries without naming the owning tool"
}

admitted contains c.row if {
	truth.py(input.hook_present)
	truth.py(input.skill_present)
	some c in input.cases
	object.get(c, "row", null) != null
}

# METADATA
# title: "R1 — the hook is installed"
deny contains msg if {
	input.hook_present == false
	msg := sprintf("R1: the structural-query hook is not installed at %v", [input.hook])
}

# METADATA
# title: "R2 — the routing table is LOCAL"
# description: |
#   The hook parses an absent file and fires with no tool named.
deny contains msg if {
	input.skill_present == false
	msg := sprintf("R2: no local routing table at %v", [input.skill])
}

# METADATA
# title: "R4 — a row's tool must exist on this machine"
# description: |
#   W243: a route naming a tool that cannot start is the failure the pyproject tooling-extra comment records
#   (the table named a capability the machine lacked). `resolves` is true, false, or null (the row names no path):
#   null is withheld below, never judged. A path outside the repo root measures false (W738).
deny contains msg if {
	some c in object.get(input, "cases", [])
	c.resolves == false
	msg := sprintf("R4: a routing row names %v, which does not exist here", [object.get(c, "tool", "?")])
}

withheld contains msg if {
	some i, c in object.get(input, "cases", [])
	object.get(c, "row", null) != null
	object.get(c, "resolves", "unset") == null
	msg := sprintf("R4: row %d: %v names no path this machine can check",[i, object.get(c, "tool", "?")])
}

# METADATA
# title: "R3 — a presence the measurement did not state is withheld, not judged"
withheld contains msg if {
	some f in flags
	object.get(input, f, null) == null
	msg := sprintf("R3: %s was not measured", [f])
}

withheld contains msg if {
	some i, c in object.get(input, "cases", [])
	object.get(c, "row", null) == null
	msg := sprintf("R3: row %d: row was not measured", [i])
}
