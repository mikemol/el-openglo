# METADATA
# title: "S0 — no pairs measured admits nothing, and the population is the declared product"
# description: |
#   The measurement is `scripts/check_selection_contrast.py --json`: the declared
#   roster (variant_roster, i.e. make_schemes.GRID), the gated keys (text +
#   semantic foregrounds drawn on [Colors:Selection]), and one case per
#   (scheme, key) — its WCAG ratio against BackgroundNormal, or `ratio: null`
#   with the reason it could not be read. A SHRINKING POPULATION IS NOT A PASSING
#   ONE: renaming one scheme's [Colors:Selection] header once took "30 of 30" to
#   "25 of 25", exit 0 (W65). Weakness: a legibility FLOOR, not a preferred colour.
package el.selection_contrast

import rego.v1

# WCAG AA large text. Raise to 4.5 (AA body) when the Selection/ForegroundActive
# token question is decided. check_selection_contrast.FLOOR mirrors this for
# check_gtk; its --selftest refuses a disagreement.
floor := 3.0

# A pair no colour can satisfy, pinned at the solver's honest best ("scheme/key":
# ratio) so a change in EITHER direction is seen: a regression below the pin, an
# improvement that must leave the table. EMPTY since W10 (2026-09-21):
# EL-Openglo-Lit/ForegroundNegative sat pinned at 2.94 until the state relation
# solved the selection field darker (3.33); the pin refused until removed.
pinned := {}

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "S0: no selection pairs were measured; the search is broken, not the theme legible"
}

deny contains msg if {
	n := count(object.get(input, "cases", []))
	n > 0
	m := count(input.roster) * count(input.keys)
	n != m
	msg := sprintf("S0: %d of %d declared pairs measured (%d schemes x %d keys)", [n, m, count(input.roster), count(input.keys)])
}

deny contains msg if {
	some c in input.cases
	c.ratio == null
	msg := sprintf("S0: %s: %s", [c.id, c.why])
}

# METADATA
# title: "S1 — every unpinned pair clears the floor"
deny contains msg if {
	some c in input.cases
	c.ratio != null
	not pinned[c.id]
	c.ratio < floor
	msg := sprintf("S1: %s: %v on %v = %.2f:1, below %.1f:1", [c.id, c.fg, c.bg, c.ratio, floor])
}

# METADATA
# title: "S2 — a pinned pair has not moved from its pin"
deny contains msg if {
	some c in input.cases
	c.ratio != null
	pin := pinned[c.id]
	abs(c.ratio - pin) > 0.05
	msg := sprintf("S2: %s: %.2f:1, pinned at %v — an improvement must leave the table", [c.id, c.ratio, pin])
}

admitted contains c.id if {
	some c in input.cases
	c.ratio != null
	not pinned[c.id]
	c.ratio >= floor
}
