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
