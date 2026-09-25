package el.palette_chain_test

import data.el.palette_chain as p
import rego.v1

# trimmed from the real tree (--json, 2026-09-23: 15 attributes, 6 variants)
good := {
	"cvd_gate_error": null, "make_palette_error": null, "make_schemes_error": null,
	"authored_env": false, "grid_is_authored": false, "grid_count": 6,
	"cases": [
		{"id": "apca_Lc", "files": ["ghost_solve.py", "make_palette.py"], "present": true},
		{"id": "wcag_ratio", "files": ["ghost_solve.py", "make_palette.py"], "present": true},
		{"id": "worst_view_dE", "files": ["make_konsole.py", "make_palette.py"], "present": true},
	],
}

test_admits_the_solved_chain if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	count(p.admitted) == 3 with input as good
}

test_k0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "K0:")
}

# THE RECOVERY'S REAL FAILURE (the docstring): 8 of 10 attributes the consumers
# call were gone, make_palette could not import, make_schemes shipped its
# authored fallback — and nothing went red. Which eight is not recorded; this
# replays the shape on today's names.
recovery := object.union(good, {
	"make_palette_error": "AttributeError: module 'cvd_gate' has no attribute 'worst_view_dE'",
	"grid_is_authored": true,
	"cases": [
		{"id": "apca_Lc", "files": ["make_palette.py"], "present": true},
		{"id": "wcag_ratio", "files": ["make_palette.py"], "present": true},
		{"id": "worst_view_dE", "files": ["make_konsole.py", "make_palette.py"], "present": false},
	],
})

test_k1_refuses_an_absent_attribute if {
	some msg in p.deny with input as recovery
	msg == "K1: C.worst_view_dE is referenced but absent (called by make_konsole.py, make_palette.py)"
}

test_k2_refuses_a_solver_that_will_not_import if {
	some msg in p.deny with input as recovery
	startswith(msg, "K2: make_palette will not import: AttributeError")
}

test_k3_refuses_the_authored_fallback if {
	some msg in p.deny with input as recovery
	msg == "K3: make_schemes is emitting the AUTHORED fallback, not solver output"
}

test_k1_refuses_cvd_gate_that_will_not_import if {
	bad := object.union(good, {"cvd_gate_error": "SyntaxError: invalid syntax"})
	some msg in p.deny with input as bad
	msg == "K1: cvd_gate will not import: SyntaxError: invalid syntax"
	count(p.admitted) == 0 with input as bad
}

test_k3_refuses_an_empty_grid if {
	some msg in p.deny with input as object.union(good, {"grid_count": 0})
	msg == "K3: the grid is empty"
}

test_k3_withholds_the_deliberate_fallback if {
	chosen := object.union(good, {"authored_env": true, "grid_is_authored": true})
	count(p.deny) == 0 with input as chosen
	some msg in p.withheld with input as chosen
	startswith(msg, "K3: EL_AUTHORED_PALETTE=1")
}
