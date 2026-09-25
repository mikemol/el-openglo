package el.consumers_test

import data.el.consumers as p
import rego.v1

ok_case(id) := {"id": id, "present": true, "imported": true, "error": null, "missing": null, "missing_is_ours": null}

good := {"cases": [ok_case("cvd_gate"), ok_case("make_palette")]}

test_admits_modules_that_import if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	p.admitted == {"cvd_gate", "make_palette"} with input as good
}

test_i0_refuses_an_absent_population if {
	some m in p.deny with input as {}
	startswith(m, "I0:")
}

test_i1_refuses_an_absent_module_file if {
	c := {"id": "glyph_match", "present": false, "imported": null, "error": null, "missing": null, "missing_is_ours": null}
	"I1: glyph_match: module file absent" in p.deny with input as {"cases": [c]}
	count(p.admitted) == 0 with input as {"cases": [c]}
}

# the defect this gate exists for: cvd_gate's attributes absent, nothing went red
test_i2_refuses_a_top_level_failure if {
	c := object.union(ok_case("make_palette"), {"imported": false, "error": "AttributeError: module 'cvd_gate' has no attribute 'stretch_lit'"})
	"I2: make_palette: AttributeError: module 'cvd_gate' has no attribute 'stretch_lit'" in p.deny with input as {"cases": [c]}
}

test_i2_refuses_a_missing_module_of_this_tree if {
	c := object.union(ok_case("make_schemes"), {"imported": false, "error": "ModuleNotFoundError: No module named 'palette_graph'", "missing": "palette_graph", "missing_is_ours": true})
	"I2: make_schemes: ModuleNotFoundError: No module named 'palette_graph' (a module of this tree)" in p.deny with input as {"cases": [c]}
}

# a missing third-party dependency is a SKIP beside the admitted ones, not a failure
test_i2_withholds_a_missing_third_party if {
	c := object.union(ok_case("render_showcase"), {"imported": false, "error": "ModuleNotFoundError: No module named 'matplotlib'", "missing": "matplotlib", "missing_is_ours": false})
	inp := {"cases": [ok_case("cvd_gate"), c]}
	"I2: render_showcase: needs matplotlib, not installed here" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
	p.admitted == {"cvd_gate"} with input as inp
}

test_all_null_case_withheld_only if {
	c := {"id": "cvd_gate", "present": null, "imported": null, "error": null, "missing": null, "missing_is_ours": null}
	"W: cvd_gate: present was not measured" in p.withheld with input as {"cases": [c]}
	count(p.deny) == 0 with input as {"cases": [c]}
	count(p.admitted) == 0 with input as {"cases": [c]}
}
