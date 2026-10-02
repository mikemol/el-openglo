# METADATA
# title: "N0 — no edge solved admits nothing"
# description: |
#   The measurement is `scripts/check_nodal.py --json`: each colour constraint
#   edge's margin (1.0 = at its floor), bound as resistance (conductance 1/m,
#   gcalc's NOT), and its effective resistance from gcalc.solver.r_eff over the
#   whole network. W221. The N1 rule tests a HYPOTHESIS (colour distance composes
#   in series), so a deny here is evidence for the operator, not yet a palette defect.
package el.nodal

import rego.v1

import data.el.fmt

deny contains "N0: no edge was solved; the population is empty, not the network sound" if {
	count(object.get(input, "cases", [])) == 0
}

deny contains msg if {
	some c in input.cases
	c.r_eff == null
	msg := sprintf("N0: %s: the solve returned no effective resistance", [c.id])
}

# METADATA
# title: "N1 — a pair that clears alone is not near through other colours"
deny contains msg if {
	some c in input.cases
	c.r_eff != null
	c.margin >= 1
	c.r_eff < 1
	msg := sprintf("N1: %s: clears alone (margin %s) but its effective resistance is %s - near through other colours", [c.id, fmt.fixed(c.margin, 2), fmt.fixed(c.r_eff, 2)])
}

withheld contains msg if {
	some msg in object.get(input, "withheld", [])
}

admitted contains c.id if {
	some c in input.cases
	c.r_eff != null
	c.r_eff >= 1
}

# an edge that does not clear alone is the per-edge gates' business, not this rule's
admitted contains c.id if {
	some c in input.cases
	c.r_eff != null
	c.margin < 1
}
