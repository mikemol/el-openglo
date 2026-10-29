# METADATA
# title: "R0 — the forced render race was not measured"
# description: |
#   The measurement is `scripts/check_render_race.py --json`: the clock rendered under three
#   harnesses, the subject Loader held inactive past the default harness's fixed grab in two of
#   them. An empty population is a broken run, not a race that does not happen.
# custom:
#   family: gate
package el.render_race

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	count(object.get(input, "withheld", [])) == 0
	msg := "R0: the forced render race was not measured"
}

# METADATA
# title: "R1 — the settled harness must be lit with the load held (W781)"
# description: |
#   The render gate grabs from the subject's load. If it reads blank when the load is late,
#   the gate again fails under load with `0 lit px`.
deny contains msg if {
	some c in object.get(input, "cases", [])
	c.name == "held-settled"
	c.lit < input.min_lit
	msg := sprintf("R1: the settled harness read %d lit px with the load held (min %d)", [c.lit, input.min_lit])
}

# METADATA
# title: "R2 — the control must be lit (W781)"
# description: |
#   A harness that reads blank when nothing is held cannot see lit pixels, so its other
#   readings say nothing.
deny contains msg if {
	some c in object.get(input, "cases", [])
	c.name == "control"
	c.lit < input.min_lit
	msg := sprintf("R2: the control read %d lit px, so the instrument cannot see (min %d)", [c.lit, input.min_lit])
}

# METADATA
# title: "R3 — the default harness must stay blank with the load held (W781)"
# description: |
#   The forcing is the proof: the old grab IS the race. If it stops reading blank, either the
#   default harness was fixed (retire this witness on purpose) or the hold stopped holding, and
#   in both cases the settled harness's pass proves nothing.
deny contains msg if {
	some c in object.get(input, "cases", [])
	c.name == "held-default"
	c.lit >= input.min_lit
	msg := sprintf("R3: the default harness read %d lit px with the load held, so the race is not forced (min %d)", [c.lit, input.min_lit])
}

withheld contains msg if {
	some w in object.get(input, "withheld", [])
	msg := sprintf("R0: not rendered: %s", [w])
}
