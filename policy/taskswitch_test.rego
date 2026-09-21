package el.taskswitch_test

import data.el.taskswitch as ts
import rego.v1

good := {"variant": "EL-Openglo", "structure": "KWin/WindowSwitcher", "id": "org.el.taskswitch.elopenglo",
	"defaults_id": "org.el.taskswitch.elopenglo", "root": true,
	"colors": {"lit": "#99ffeb", "ghost": "#7ed3c3", "void": "#081411"}, "alpha": 0.566, "lint": []}

clean := {"qmllint": true, "variants": [good]}

test_admits_clean if {
	count(ts.deny) == 0 with input as clean
	count(ts.withheld) == 0 with input as clean
}

test_t0_refuses_empty if {
	some msg in ts.deny with input as {"qmllint": true, "variants": []}
	startswith(msg, "T0:")
}

test_t1_refuses_wrong_structure if {
	some msg in ts.deny with input as {"qmllint": true, "variants": [object.union(good, {"structure": "Plasma/Applet"})]}
	contains(msg, "KPackageStructure")
}

test_t1_refuses_an_id_the_defaults_do_not_name if {
	some msg in ts.deny with input as {"qmllint": true, "variants": [object.union(good, {"defaults_id": "org.el.other"})]}
	contains(msg, "defaults name")
}

test_t2_refuses_a_missing_root if {
	some msg in ts.deny with input as {"qmllint": true, "variants": [object.union(good, {"root": false})]}
	contains(msg, "TabBoxSwitcher")
}

test_t2_refuses_a_lint_error if {
	some msg in ts.deny with input as {"qmllint": true, "variants": [object.union(good, {"lint": ["taskswitch-main.qml:3:1: [syntax] Expected token"]})]}
	contains(msg, "syntax")
}

test_t3_refuses_an_unfilled_hole if {
	some msg in ts.deny with input as {"qmllint": true, "variants": [object.union(good, {"colors": {"lit": null, "ghost": "#7ed3c3", "void": "#081411"}})]}
	contains(msg, "unfilled")
}

test_t3_refuses_indistinct_colours if {
	some msg in ts.deny with input as {"qmllint": true, "variants": [object.union(good, {"colors": {"lit": "#111111", "ghost": "#111111", "void": "#111111"}})]}
	contains(msg, "distinct")
}

test_t3_refuses_an_out_of_range_alpha if {
	some msg in ts.deny with input as {"qmllint": true, "variants": [object.union(good, {"alpha": 1.5})]}
	contains(msg, "ghostAlpha")
}

test_withheld_without_qmllint if {
	inp := {"qmllint": false, "variants": [good]}
	count(ts.deny) == 0 with input as inp
	count(ts.withheld) == 1 with input as inp
}
