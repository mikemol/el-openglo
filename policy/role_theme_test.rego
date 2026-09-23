package el.role_theme_test

import data.el.role_theme as p
import rego.v1

roles := ["read", "write", "flow"]

hexes := {"read": "#0072b2", "write": "#009e73", "flow": "#56b4e9"}

# the real tree's shape (--json, 2026-09-23), cut to three roles
good := {
	"roles": roles, "pinned": {}, "pins_hold": {},
	"assignment": {"read": "blue", "write": "bluegreen", "flow": "sky"},
	"worst_q": 1.4936, "best_q": 1.4936, "best_assignment": {"read": "blue", "write": "bluegreen", "flow": "sky"},
	"json": {"error": null, "fields": ["assignment", "roles", "worst_q", "metric", "solved_exhaustively"], "assignment": hexes},
	"ground": {"refused": null, "ground": "#ffffff", "contrast": {"read": 5.19, "write": 3.42}, "pins_hold": {"roundtrip": true}},
	"render": {"withheld": null, "error": null, "survives": {"read": true, "write": true, "flow": true}},
	"cases": [{"id": r} | some r in roles],
}

test_admits_an_optimal_theme_that_renders if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	p.admitted == {"read", "write", "flow"} with input as good
}

# graphviz absent on this host: the render is withheld, the roles still admitted
test_r5_withholds_the_render_without_graphviz if {
	w := object.union(good, {"render": {"withheld": "graphviz `dot` is not installed", "error": null, "survives": {}}})
	count(p.deny) == 0 with input as w
	some msg in p.withheld with input as w
	startswith(msg, "R5: render unverified")
	count(p.admitted) == 3 with input as w
}

# exactly-once (rego_lint N1): a role present with a null value was NOT MEASURED —
# withheld, never "unassigned" (the old `not input.assignment[r]` denied it) and
# never admitted
test_null_assignment_is_withheld_not_unassigned if {
	w := object.union(good, {"assignment": {"read": "blue", "write": "bluegreen", "flow": null}})
	"R1: assignment[\"flow\"] was not measured" in p.withheld with input as w
	not "R1: role \"flow\" is declared but unassigned" in p.deny with input as w
	not "flow" in p.admitted with input as w
}

test_r0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "R0:")
}

test_r1_refuses_an_unassigned_role if {
	bad := object.union(object.remove(good, ["assignment"]), {"assignment": {"read": "blue", "write": "bluegreen"}})
	some msg in p.deny with input as bad
	msg == "R1: role \"flow\" is declared but unassigned"
}

# the selftest's refusing fixture: a hand assignment claiming a score 0.5 under
# what the pool allows
test_r2_refuses_a_sub_optimal_assignment if {
	bad := object.union(good, {"worst_q": 0.9936})
	some msg in p.deny with input as bad
	startswith(msg, "R2: a better assignment exists (q=1.4936 > 0.9936)")
	count(p.admitted) == 0 with input as bad
}

# whole-number scores print as fixed point, never %!f(int=…)
test_r2_message_formats_whole_numbers if {
	some msg in p.deny with input as object.union(good, {"worst_q": 1, "best_q": 2})
	startswith(msg, "R2: a better assignment exists (q=2.0000 > 1.0000)")
	not contains(msg, "%!")
}

test_r3_refuses_a_missing_field if {
	bad := object.union(good, {"json": object.union(good.json, {"fields": ["assignment", "roles", "worst_q", "metric"]})})
	some msg in p.deny with input as bad
	startswith(msg, "R3: the emitted JSON omits \"solved_exhaustively\"")
}

test_r3_refuses_a_non_hex_colour if {
	bad := object.union(good, {"json": object.union(good.json, {"assignment": object.union(hexes, {"flow": "sky"})})})
	some msg in p.deny with input as bad
	msg == "R3: assignment[\"flow\"] = sky is not a #rrggbb hex"
}

# the selftest's grounded fixture: read at 1.32:1 on white
test_r4_refuses_a_grounded_role_under_3_to_1 if {
	bad := object.union(good, {"ground": object.union(good.ground, {"contrast": {"read": 1.32, "write": 3.42}})})
	some msg in p.deny with input as bad
	msg == "R4: grounded: read is 1.32:1 against white, below the 3:1 non-text minimum it claims to satisfy"
}

# five FREE roles on white: four eligible members, the solve refuses
test_r4_refuses_a_grounded_solve_that_refused if {
	bad := object.union(good, {"ground": {"refused": "4 eligible members for 5 free roles", "ground": null, "contrast": {}, "pins_hold": {}}})
	some msg in p.deny with input as bad
	startswith(msg, "R4: the grounded solve refuses")
}

test_r4_refuses_a_broken_grounded_pin if {
	bad := object.union(good, {"ground": object.union(good.ground, {"pins_hold": {"roundtrip": false}})})
	some msg in p.deny with input as bad
	startswith(msg, "R4: grounded: \"roundtrip\" is pinned")
}

# the REAL first-version defect: `edgecolor=` — graphviz has no such attribute,
# the file rendered, and every edge came out default black
test_r5_refuses_a_colour_lost_in_the_render if {
	bad := object.union(good, {"render": {"withheld": null, "error": null, "survives": {"read": false, "write": true, "flow": true}}})
	some msg in p.deny with input as bad
	startswith(msg, "R5: read's colour does not survive into the render")
	p.admitted == {"write", "flow"} with input as bad
}

test_r5_refuses_a_dot_that_does_not_render if {
	bad := object.union(good, {"render": {"withheld": null, "error": "dot exited 1: syntax error", "survives": {}}})
	some msg in p.deny with input as bad
	startswith(msg, "R5: the emitted .dot does not render")
}
