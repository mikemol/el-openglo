# METADATA
# title: "D0 — no pairs measured admits nothing, and the population is the declared product"
# description: |
#   The measurement is `scripts/check_separation.py --json`: the variants
#   (make_schemes.GRID), the ENFORCED pair names (cvd_gate.ENFORCED, the
#   palette_graph projection), the reference floor in CAM02-UCS dE, and one case
#   per (variant, pair) — its worst-view dE under the CVD simulations and the
#   view that collapses it, or `dE: null` with why. ENFORCED pairs are those
#   where colour is the SOLE carrier; SURFACED pairs are reported, never gated.
#   Weakness: this gates the pairs the authority DECLARES, not the pairs that
#   matter (check_palette_graph --edges shows the ungated ones).
package el.separation

import data.el.fmt
import rego.v1

# the share of the reference floor an enforced pair must clear
# (cvd_gate.audit_variant's `factor`, the design's number)
factor := 0.8

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "D0: no enforced pairs were measured; the search is broken, not the palette clean"
}

deny contains msg if {
	n := count(object.get(input, "cases", []))
	n > 0
	m := count(input.variants) * count(input.enforced)
	n != m
	msg := sprintf("D0: %d of %d declared pairs measured (%d variants x %d pairs)", [n, m, count(input.variants), count(input.enforced)])
}

deny contains msg if {
	some c in input.cases
	c.dE == null
	msg := sprintf("D0: %s: %s", [c.id, c.why])
}

# METADATA
# title: "D1 — every enforced pair clears the CVD separation floor"
deny contains msg if {
	some c in input.cases
	c.dE != null
	c.dE < input.floor * factor
	msg := sprintf("D1: %s: dE %s < %s (%s)", [c.id, fmt.fixed(c.dE, 1), fmt.fixed(input.floor * factor, 1), c.view])
}

admitted contains c.id if {
	some c in input.cases
	c.dE != null
	c.dE >= input.floor * factor
}
