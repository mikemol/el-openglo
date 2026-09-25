# METADATA
# title: "K0 — no cvd_gate references found admits nothing"
# description: |
#   The measurement is `scripts/check_palette_chain.py --json`: per attribute the
#   tree reads off cvd_gate (an AST walk over the tracked .py files), its callers
#   and whether cvd_gate has it; each of cvd_gate / make_palette / make_schemes'
#   import error or null; whether make_schemes.GRID IS its _AUTHORED_GRID fallback
#   and how many variants it holds; and whether EL_AUTHORED_PALETTE=1 selected the
#   fallback deliberately. The recovery lost 8 of the 10 attributes and every gate
#   stayed green while the authored table shipped. Weakness: SHIPPED is the
#   module's own state, not the emitted files.
package el.palette_chain

import rego.v1

deny contains "K0: no cvd_gate references were found; the walk is broken, not the chain healthy" if {
	count(object.get(input, "cases", [])) == 0
}

# METADATA
# title: "K1 — API: cvd_gate imports and has every attribute the tree calls"
deny contains msg if {
	e := object.get(input, "cvd_gate_error", null)
	e != null
	msg := sprintf("K1: cvd_gate will not import: %s", [e])
}

deny contains msg if {
	object.get(input, "cvd_gate_error", null) == null
	some c in input.cases
	c.present != true
	msg := sprintf("K1: C.%s is referenced but absent (called by %s)", [c.id, concat(", ", c.files)])
}

# METADATA
# title: "K2 — SOLVE: make_palette imports"
deny contains msg if {
	e := object.get(input, "make_palette_error", null)
	e != null
	msg := sprintf("K2: make_palette will not import: %s", [e])
}

# METADATA
# title: "K3 — SHIPPED: make_schemes emits the solved grid, not the authored fallback"
deny contains msg if {
	e := object.get(input, "make_schemes_error", null)
	e != null
	msg := sprintf("K3: make_schemes will not import: %s", [e])
}

deny contains "K3: make_schemes is emitting the AUTHORED fallback, not solver output" if {
	object.get(input, "authored_env", false) != true
	object.get(input, "grid_is_authored", null) == true
}

deny contains "K3: the grid is empty" if {
	object.get(input, "make_schemes_error", null) == null
	object.get(input, "grid_count", null) == 0
}

withheld contains "K3: EL_AUTHORED_PALETTE=1 selects the fallback deliberately (the residue path, not a defect)" if {
	object.get(input, "authored_env", false) == true
}

admitted contains c.id if {
	object.get(input, "cvd_gate_error", null) == null
	some c in input.cases
	c.present == true
}
