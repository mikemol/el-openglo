package el.relations_test

import data.el.relations as p
import rego.v1

good := {
	"known": ["view", "fg", "sel_bg"],
	"terminals": ["view"],
	"free": ["fg", "sel_bg"],
	"open_questions": 2,
	"netlist": [{"key": "view~fg", "pair": true, "generator": "wcag"}],
	"cases": [
		{"u": "view", "v": "fg", "kind": "floor", "quantity": "wcag_ratio", "bound": "4.6"},
		{"u": "fg", "v": "sel_bg", "kind": "balance", "quantity": "q", "bound": null},
	],
}

test_admits_a_well_formed_set if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 2 with input as good
}

test_r0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "R0:")
}

# the old selftest's first fixture: a relation naming a role the authority does not declare
test_r1_refuses_an_invented_role if {
	bad := object.union(good, {"cases": [{"u": "view", "v": "no_such_role", "kind": "floor", "quantity": "wcag_ratio", "bound": "4.6"}]})
	some msg in p.deny with input as bad
	msg == "R1: view~no_such_role (floor): names \"no_such_role\", which the edge authority does not"
}

test_r2_refuses_a_floor_with_no_bound if {
	bad := object.union(good, {"cases": [{"u": "view", "v": "fg", "kind": "floor", "quantity": "wcag_ratio", "bound": null}]})
	some msg in p.deny with input as bad
	msg == "R2: view~fg: a floor relation with no bound cannot be checked"
}

test_r2_refuses_no_quantity if {
	bad := object.union(good, {"cases": [{"u": "view", "v": "fg", "kind": "floor", "quantity": "", "bound": "4.6"}]})
	some msg in p.deny with input as bad
	startswith(msg, "R2: view~fg: names no quantity")
}

test_r3_refuses_pinned_and_free if {
	some msg in p.deny with input as object.union(good, {"terminals": ["view", "fg"]})
	msg == "R3: \"fg\" is pinned AND free — a node cannot be both"
}

# the old selftest's view_alt fixture: a free node no relation reaches
test_r4_refuses_an_unreached_free_node if {
	bad := object.union(good, {"known": ["view", "fg", "sel_bg", "view_alt"], "free": ["fg", "sel_bg", "view_alt"]})
	some msg in p.deny with input as bad
	msg == "R4: \"view_alt\" is free but no relation reaches it — undetermined"
}

test_r5_refuses_an_empty_handoff if {
	some msg in p.deny with input as object.union(good, {"netlist": []})
	startswith(msg, "R5:")
}

test_r6_refuses_hidden_gaps if {
	some msg in p.deny with input as object.union(good, {"open_questions": 0})
	startswith(msg, "R6:")
}
