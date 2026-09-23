# METADATA
# title: "A0 — no variants measured admits nothing"
# description: |
#   The measurement is `scripts/check_aperture.py --json`: per variant, the three
#   pips of the aperture probe (clear / half / covered) as seen and as the scheme
#   says they should read, with the per-channel max error.
package el.aperture

import rego.v1

import data.el.truth

deny contains msg if {
	# absent counts as empty: count(input.variants) is UNDEFINED on {}, and an
	# undefined rule body admits (measured s131 by opa_gate's selftest)
	count(object.get(input, "variants", [])) == 0
	msg := "A0: no variants were measured"
}

# ⚑ EVERY VARIANT LANDS IN EXACTLY ONE OF withheld / deny / admitted:
#   withheld  A1  it could not be rendered (a withholding reason)
#             A5  it rendered, but a pip's error is null / absent / not a number
#   deny      A2-A4  a measured pip's error is over its tolerance
#   admitted      every pip measured and within tolerance
# A null / "" withheld is NOT a withholding reason (`not v.withheld` read null as
# one); a null error is NOT a pass (`null > 2` is false, so it was silently
# neither denied nor admitted).

pips := {"clear": 2, "half": 3, "covered": 2}

label(v) := object.get(v, "variant", "?")

rendered(v) if not truth.py(object.get(v, "withheld", null))

at(v, part, k) := x if {
	e := object.get(v, part, null)
	is_object(e)
	x := object.get(e, k, null)
} else := null

err(v, k) := at(v, "error", k)

unmeasured(v) := {k | some k, _ in pips; not is_number(err(v, k))}

measured(v) if {
	rendered(v)
	count(unmeasured(v)) == 0
}

over(v, k) if {
	is_number(err(v, k))
	err(v, k) > pips[k]
}

# METADATA
# title: "A1 — a variant that could not be rendered is withheld, not judged"
withheld contains msg if {
	some v in input.variants
	truth.py(object.get(v, "withheld", null))
	msg := sprintf("A1: %s: %s", [label(v), v.withheld])
}

# METADATA
# title: "A5 — a rendered variant whose pip error was not measured is withheld"
withheld contains msg if {
	some v in input.variants
	rendered(v)
	count(unmeasured(v)) > 0
	msg := sprintf("A5: %s: error %v was not measured", [label(v), sort(unmeasured(v))])
}

admitted contains label(v) if {
	some v in input.variants
	measured(v)
	count({k | some k, _ in pips; over(v, k)}) == 0
}

# METADATA
# title: "A2 — the clear pip is the ghost floor"
# description: |
#   A pip with nothing behind it reads ghost composited over the ground at the
#   palette's global ghost alpha, within 2 (rounding across the composite).
deny contains msg if {
	some v in input.variants
	measured(v)
	over(v, "clear")
	msg := sprintf("A2: %s: the clear pip reads %v, not the ghost floor %v", [label(v), at(v, "seen", "clear"), at(v, "expected", "clear")])
}

# METADATA
# title: "A3 — the half-covered pip is halfway"
# description: |
#   The block's edge sits exactly half a pip into its column; that pip must read
#   the floor plus half the way to lit — the brightness RANGE the field exists
#   for. A snapping field reads it as floor or as lit and fails here. Within 3.
deny contains msg if {
	some v in input.variants
	measured(v)
	over(v, "half")
	msg := sprintf("A3: %s: the half pip reads %v, not halfway %v", [label(v), at(v, "seen", "half"), at(v, "expected", "half")])
}

# METADATA
# title: "A4 — the covered pip is the lit token"
deny contains msg if {
	some v in input.variants
	measured(v)
	over(v, "covered")
	msg := sprintf("A4: %s: the covered pip reads %v, not the lit token %v", [label(v), at(v, "seen", "covered"), at(v, "expected", "covered")])
}
