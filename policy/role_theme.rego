# METADATA
# title: "R0 — no roles declared admits nothing"
# description: |
#   The measurement is `scripts/check_role_theme.py --json`: the consumer's
#   declared roles and pins, the solved assignment and its worst-pair score
#   beside the EXHAUSTIVE best over the pool, the emitted JSON as a consumer
#   reads it (without cvd_gate), the grounded (on-white) solve, and whether the
#   emitted .dot renders with every role's colour surviving into the SVG
#   (graphviz absent withholds). ⚑ OPTIMALITY IS THE PROPERTY: every assignment
#   of these roles over Okabe-Ito clears the floor, so `q >= 1` could not fail.
#   Weakness: optimal FOR THE ROLES GIVEN; whether a consumer should adopt it is
#   not measured.
package el.role_theme

import data.el.fmt
import rego.v1

# the fields a consumer needs to tell what was solved and how
json_fields := {"assignment", "roles", "worst_q", "metric", "solved_exhaustively"}

# the non-text minimum the grounded artifact claims against white
ground_floor := 3.0

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "R0: no roles were declared; the search is broken, not the theme optimal"
}

# METADATA
# title: "R1 — every declared role is assigned, and every pin holds"
deny contains msg if {
	some r in input.roles
	not input.assignment[r]
	msg := sprintf("R1: role %q is declared but unassigned", [r])
}

deny contains msg if {
	some r, held in input.pins_hold
	not held
	msg := sprintf("R1: %q is pinned to %q but carries a different colour", [r, input.pinned[r]])
}

# METADATA
# title: "R2 — no other assignment scores better (optimality)"
deny contains msg if {
	input.best_q > input.worst_q + 1e-12
	msg := sprintf("R2: a better assignment exists (q=%s > %s): %v — the emitted theme is not optimal", [fmt.fixed(input.best_q, 4), fmt.fixed(input.worst_q, 4), input.best_assignment])
}

# METADATA
# title: "R3 — the emitted JSON parses and carries what a consumer needs"
deny contains msg if {
	input.json.error != null
	msg := sprintf("R3: the emitted JSON does not parse: %s", [input.json.error])
}

deny contains msg if {
	input.json.error == null
	some f in json_fields
	not f in {x | some x in input.json.fields}
	msg := sprintf("R3: the emitted JSON omits %q, so a consumer cannot tell what was solved or how", [f])
}

deny contains msg if {
	some r in input.roles
	not is_hex(input.json.assignment[r])
	msg := sprintf("R3: assignment[%q] = %v is not a #rrggbb hex", [r, input.json.assignment[r]])
}

is_hex(v) if {
	is_string(v)
	regex.match(`^#[0-9a-fA-F]{6}$`, v)
}

# METADATA
# title: "R4 — the grounded artifact clears the ground it names"
deny contains msg if {
	input.ground.refused != null
	msg := sprintf("R4: the grounded solve refuses: %s", [input.ground.refused])
}

deny contains msg if {
	input.ground.refused == null
	input.ground.ground != "#ffffff"
	msg := sprintf("R4: the grounded artifact records ground=%v, so a consumer cannot tell which objective it answers", [input.ground.ground])
}

deny contains msg if {
	some r, ratio in input.ground.contrast
	ratio < ground_floor
	msg := sprintf("R4: grounded: %s is %s:1 against white, below the %s:1 non-text minimum it claims to satisfy", [r, fmt.fixed(ratio, 2), fmt.fixed(ground_floor, 0)])
}

deny contains msg if {
	some r, held in input.ground.pins_hold
	not held
	msg := sprintf("R4: grounded: %q is pinned and differs from its target", [r])
}

# METADATA
# title: "R5 — the .dot renders, and every role's colour survives into the render"
withheld contains msg if {
	input.render.withheld != null
	msg := sprintf("R5: render unverified — %s", [input.render.withheld])
}

deny contains msg if {
	input.render.error != null
	msg := sprintf("R5: the emitted .dot does not render: %s", [input.render.error])
}

deny contains msg if {
	some r, kept in input.render.survives
	not kept
	msg := sprintf("R5: %s's colour does not survive into the render — the file loads and the colour is not in it", [r])
}

admitted contains c.id if {
	some c in input.cases
	input.assignment[c.id]
	is_hex(input.json.assignment[c.id])
	input.best_q <= input.worst_q + 1e-12
	object.get(input.render.survives, c.id, true)
}
