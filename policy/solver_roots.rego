# METADATA
# title: "R0 — no slot side measured admits nothing"
# description: |
#   The measurement is `scripts/check_solver_roots.py --json`: per (variant,
#   field, slot, side) the best WCAG contrast reachable anywhere in the slot's
#   sector on that side of the field, and the best the solver's candidate set
#   offers there. W220: |contrast| >= floor has two roots (lighter and darker),
#   and the candidates must cover every root that exists.
package el.solver_roots

import rego.v1

import data.el.fmt

deny contains "R0: no slot side was measured; the population is empty, not the solver complete" if {
	count(object.get(input, "cases", [])) == 0
}

# METADATA
# title: "R1 — a reachable root is covered: a side that can clear the floor has a candidate that does"
deny contains msg if {
	some c in input.cases
	c.reachable >= input.floor
	not covered(c)
	msg := sprintf("R1: %s: the %s root reaches %s >= %s but the candidates offer %v there (%d candidates; %v before the accent prune; most saturated clearing sat %v)", [c.id, c.side, fmt.fixed(c.reachable, 2), fmt.fixed(input.floor, 2), c.candidate, c.n_candidates, object.get(c, "n_unpruned", null), object.get(c, "reachable_sat_min", null)])
}

covered(c) if {
	c.candidate != null
	c.candidate >= input.floor
}

# a side no colour in the sector can lift to the floor is not a root; nothing to cover
admitted contains c.id if {
	some c in input.cases
	c.reachable < input.floor
}

admitted contains c.id if {
	some c in input.cases
	covered(c)
}
