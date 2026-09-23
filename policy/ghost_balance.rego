# METADATA
# title: "B0 — no variants measured admits nothing"
# description: |
#   The measurement is `scripts/check_ghost_balance.py --json`: per shipped
#   variant, the worse side (max-min objective) of cvd_gate's 99-point SCAN and
#   of ghost_solve's closed-form SOLVE (y = sqrt(ab)), the ideal, and the solve's
#   skew (how far its two sides differ). The scan's defect is its silence: it
#   cannot be shown wrong. The solve can, against the balance condition.
#   Weakness: solving luminance is exact, reaching it with an 8-bit triple is
#   not, so a residual skew is bounded, not forbidden.
package el.ghost_balance

import rego.v1

# the residual an 8-bit segment can leave after an exact luminance solve;
# check_ghost_balance.MAX_SKEW mirrors it for its fixtures (--selftest compares)
max_skew := 1.06

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "B0: no variants were measured; the grid is not built, not the ghost balanced"
}

# METADATA
# title: "B1 — the solve never loses to the scan on the shared objective"
deny contains msg if {
	some c in input.cases
	c.solve < c.scan - 1e-9
	msg := sprintf("B1: %s: solved worst side %.4f < scanned %.4f", [c.id, c.solve, c.scan])
}

# METADATA
# title: "B2 — the solve balances, to within what 8-bit quantisation allows"
deny contains msg if {
	some c in input.cases
	c.skew > max_skew
	msg := sprintf("B2: %s: sides differ by %.4fx (> %v); the ghost is not at the balance point", [c.id, c.skew, max_skew])
}

admitted contains c.id if {
	some c in input.cases
	c.solve >= c.scan - 1e-9
	c.skew <= max_skew
}
