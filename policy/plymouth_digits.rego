# METADATA
# title: "P0 — no digits measured admits nothing"
# description: |
#   The measurement is `scripts/check_plymouth_digits.py --json`: per digit, the
#   substrate's 7-seg projection (segment_topology.project(glyph16(d), "7")) and
#   make_plymouth.SEVENSEG's own entry, or no cases and the `error` that stopped
#   the read. Plymouth imports the substrate and carried its own digit table
#   anyway; this is the join. Weakness: glyphs, not pixels — the renderer's
#   polygon is not compared.
package el.plymouth_digits

import rego.v1

# the digits the splash draws: every one must be compared
digits := {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := sprintf("P0: no digits were measured (%v); the search is broken, not the splash faithful", [object.get(input, "error", null)])
}

# METADATA
# title: "P0 — the population is every digit, no fewer"
deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	measured := {c.id | some c in input.cases}
	lost := digits - measured
	count(lost) > 0
	msg := sprintf("P0: %d of %d digits measured; missing %v", [count(digits & measured), count(digits), sort(lost)])
}

# METADATA
# title: "P1 — plymouth lights exactly the substrate's segments"
deny contains msg if {
	some c in input.cases
	c.substrate != c.plymouth
	msg := sprintf("P1: '%s': substrate %s vs plymouth %s", [c.id, concat("", c.substrate), concat("", c.plymouth)])
}

admitted contains c.id if {
	some c in input.cases
	c.substrate == c.plymouth
}
