# METADATA
# title: "A0 — no variants measured admits nothing"
# description: |
#   The measurement is `scripts/check_aperture.py --json`: per variant, the three
#   pips of the aperture probe (clear / half / covered) as seen and as the scheme
#   says they should read, with the per-channel max error.
package el.aperture

import rego.v1

deny contains msg if {
	# absent counts as empty: count(input.variants) is UNDEFINED on {}, and an
	# undefined rule body admits (measured s131 by opa_gate's selftest)
	count(object.get(input, "variants", [])) == 0
	msg := "A0: no variants were measured"
}

# METADATA
# title: "A1 — a variant that could not be rendered is withheld, not judged"
withheld contains msg if {
	some v in input.variants
	v.withheld
	msg := sprintf("A1: %s: %s", [v.variant, v.withheld])
}

# METADATA
# title: "A2 — the clear pip is the ghost floor"
# description: |
#   A pip with nothing behind it reads ghost composited over the ground at the
#   palette's global ghost alpha, within 2 (rounding across the composite).
deny contains msg if {
	some v in input.variants
	not v.withheld
	v.error.clear > 2
	msg := sprintf("A2: %s: the clear pip reads %v, not the ghost floor %v", [v.variant, v.seen.clear, v.expected.clear])
}

# METADATA
# title: "A3 — the half-covered pip is halfway"
# description: |
#   The block's edge sits exactly half a pip into its column; that pip must read
#   the floor plus half the way to lit — the brightness RANGE the field exists
#   for. A snapping field reads it as floor or as lit and fails here. Within 3.
deny contains msg if {
	some v in input.variants
	not v.withheld
	v.error.half > 3
	msg := sprintf("A3: %s: the half pip reads %v, not halfway %v", [v.variant, v.seen.half, v.expected.half])
}

# METADATA
# title: "A4 — the covered pip is the lit token"
deny contains msg if {
	some v in input.variants
	not v.withheld
	v.error.covered > 2
	msg := sprintf("A4: %s: the covered pip reads %v, not the lit token %v", [v.variant, v.seen.covered, v.expected.covered])
}
