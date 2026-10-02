# METADATA
# title: "N0 — no variant measured admits nothing"
# description: |
#   The measurement is `scripts/check_nodal.py --json`: per variant, every
#   single-slot candidate swap in the window semantic set, and how many of them
#   leave the separation objective unchanged under the shipped hard max-min and
#   under gcalc SERIES composition (AND = 1/sum(1/q), margins as conductances).
#   W221. gcalc's position (machine.py:424): "the conductance solve IS the
#   physics, min is its shadow". An objective blind to a move cannot steer the
#   solve through it.
#
#   ⚑ RETIRED: N1 judged effective resistance over the graph topology (margin as
#   resistance). That reading was refuted on 2026-10-02 - it measures how
#   connected two colours are, not how separated - and is not restated.
package el.nodal

import rego.v1

deny contains "N0: no variant was measured; the population is empty, not the objective sound" if {
	count(object.get(input, "cases", [])) == 0
}

deny contains msg if {
	some c in input.cases
	c.moves == 0
	msg := sprintf("N0: %s: no single-slot move was tried; the candidate search is empty", [c.variant])
}

# METADATA
# title: "N2 — the series objective sees every single-slot move"
deny contains msg if {
	some c in input.cases
	c.flat_series > 0
	msg := sprintf("N2: %s: the series objective is blind to %d of %d single-slot moves", [c.variant, c.flat_series, c.moves])
}

admitted contains c.variant if {
	some c in input.cases
	c.moves > 0
	c.flat_series == 0
}
