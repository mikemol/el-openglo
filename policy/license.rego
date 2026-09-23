# METADATA
# title: "L0 — no measured declaration admits nothing"
# description: |
#   The measurement is `scripts/check_license.py --json`: every place the project
#   declares its licence (the emitters.LICENSE_SPDX authority, each generator's
#   metadata site, LICENSE / pyproject.toml / the ebuild). An empty population is
#   a broken search, not a clean tree. Third-party licences are outside it.
package el.license

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "L0: no licence declaration was measured"
}

# METADATA
# title: "L0 — every declaration kind is present"
# description: |
#   A kind with no case means its reader stopped answering (the constant was
#   renamed, the generators' sites moved to a shape the walker cannot see, the
#   LICENSE file vanished); the other kinds passing must not hide that.
deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	some kind in {"authority", "generator", "file"}
	count([c | some c in input.cases; c.kind == kind]) == 0
	msg := sprintf("L0: no %s declaration was measured", [kind])
}

# METADATA
# title: "L1 — every declaration is Apache-2.0"
# description: |
#   Operator, 2026-09-22 (W44): the project is Apache-2.0, not GPL-3. An id of
#   null is a declaration the measurement could not resolve — refused, since an
#   unreadable licence is not a correct one.
deny contains msg if {
	some c in input.cases
	c.id != "Apache-2.0"
	msg := sprintf("L1: %s declares %v, not Apache-2.0", [c.where, c.id])
}

# METADATA
# title: "L2 — a generator names the constant, never a literal"
# description: |
#   One declared id, imported by every emitter: a literal Apache-2.0 is correct
#   today and is the N-th copy the next relicence must find by hand.
deny contains msg if {
	some c in input.cases
	c.kind == "generator"
	c.via != "LICENSE_SPDX"
	msg := sprintf("L2: %s spells its licence (%s) instead of naming emitters.LICENSE_SPDX", [c.where, c.via])
}
