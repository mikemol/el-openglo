# METADATA
# title: "I0 — no module measured admits nothing"
# description: |
#   The measurement is `scripts/check_consumers.py --json`: per module of the
#   research pipeline and the colour chain (check_consumers.MODULES), whether its
#   file exists and what importing it did — imported, or the exception, and for a
#   ModuleNotFoundError the missing name and whether it is a module of this tree.
#   Importing runs the top level, so this is stronger than compiling; it is still
#   not a test of what the module computes.
package el.consumers

import rego.v1

deny contains "I0: no module was measured; the roster is empty, not the pipeline wired" if {
	count(object.get(input, "cases", [])) == 0
}

# METADATA
# title: "I1 — every roster module's file exists"
deny contains msg if {
	some c in input.cases
	c.present == false
	msg := sprintf("I1: %s: module file absent", [c.id])
}

# METADATA
# title: "I2 — every module imports; a missing module OF THIS TREE is a defect"
deny contains msg if {
	some c in input.cases
	c.imported == false
	not is_string(c.missing)
	msg := sprintf("I2: %s: %s", [c.id, c.error])
}

deny contains msg if {
	some c in input.cases
	c.imported == false
	is_string(c.missing)
	c.missing_is_ours == true
	msg := sprintf("I2: %s: %s (a module of this tree)", [c.id, c.error])
}

# a missing THIRD-PARTY dependency is a fact about this machine: a SKIP, counted
withheld contains msg if {
	some c in input.cases
	c.imported == false
	is_string(c.missing)
	c.missing_is_ours == false
	msg := sprintf("I2: %s: needs %s, not installed here", [c.id, c.missing])
}

withheld contains msg if {
	some c in input.cases
	not is_boolean(object.get(c, "present", null))
	msg := sprintf("W: %s: present was not measured", [c.id])
}

withheld contains msg if {
	some c in input.cases
	c.present == true
	not is_boolean(object.get(c, "imported", null))
	msg := sprintf("W: %s: imported was not measured", [c.id])
}

admitted contains c.id if {
	some c in input.cases
	c.present == true
	c.imported == true
}
