package el.taskswitch_test

import data.el.taskswitch as ts
import rego.v1

roles := {"lit": "textColor", "ghost": "disabledTextColor", "void": "backgroundColor"}

clean := {"qmllint": true, "structure": "KWin/WindowSwitcher", "id": "org.el.taskswitch",
	"defaults_id": "org.el.taskswitch", "root": true, "roles": roles, "colorSet": "View",
	"bindings": {"lit": "Kirigami.Theme.textColor", "ghost": "Kirigami.Theme.disabledTextColor", "void": "Kirigami.Theme.backgroundColor"},
	"alpha": 0.566, "lint": [], "roster_drift": [],
	"resolution": {"EL-Amber": {"resolved": {"lit": "#ffd499", "ghost": "#e5bf89", "void": "#140f08"},
		"expected": {"lit": "#ffd499", "ghost": "#e5bf89", "void": "#140f08"}}}}

test_t5_refuses_a_binding_that_resolves_elsewhere if {
	bad := object.union(clean, {"resolution": {"EL-Amber": {"resolved": {"lit": "#140f08", "ghost": "#e5bf89", "void": "#140f08"},
		"expected": {"lit": "#ffd499", "ghost": "#e5bf89", "void": "#140f08"}}}})
	some msg in ts.deny with input as bad
	contains(msg, "T5: under EL-Amber, lit resolves to #140f08")
}

test_t5_withheld_without_a_runner if {
	inp := object.union(clean, {"resolution": null})
	count(ts.deny) == 0 with input as inp
	count(ts.withheld) == 1 with input as inp
}

test_admits_clean if {
	count(ts.deny) == 0 with input as clean
	count(ts.withheld) == 0 with input as clean
}

test_t0_refuses_unmeasured if {
	some msg in ts.deny with input as {"qmllint": true, "roles": roles, "bindings": {}}
	startswith(msg, "T0:")
}

test_t1_refuses_wrong_structure if {
	some msg in ts.deny with input as object.union(clean, {"structure": "Plasma/Applet"})
	contains(msg, "KPackageStructure")
}

test_t1_refuses_an_id_the_defaults_do_not_name if {
	some msg in ts.deny with input as object.union(clean, {"defaults_id": "org.el.other"})
	contains(msg, "defaults name")
}

test_t2_refuses_a_missing_root if {
	some msg in ts.deny with input as object.union(clean, {"root": false})
	contains(msg, "TabBoxSwitcher")
}

test_t2_refuses_a_lint_error if {
	some msg in ts.deny with input as object.union(clean, {"lint": ["taskswitch-main.qml:3:1: [syntax] Expected token"]})
	contains(msg, "syntax")
}

test_t3_refuses_an_out_of_range_alpha if {
	some msg in ts.deny with input as object.union(clean, {"alpha": 1.5})
	contains(msg, "ghostAlpha")
}

test_t4_refuses_a_baked_hex if {
	baked := object.union(clean, {"bindings": {"lit": "#99ffeb", "ghost": "Kirigami.Theme.disabledTextColor", "void": "Kirigami.Theme.backgroundColor"}})
	some msg in ts.deny with input as baked
	contains(msg, "T4: lit is #99ffeb")
}

test_t4_refuses_the_wrong_role if {
	wrong := object.union(clean, {"bindings": {"lit": "Kirigami.Theme.highlightColor", "ghost": "Kirigami.Theme.disabledTextColor", "void": "Kirigami.Theme.backgroundColor"}})
	some msg in ts.deny with input as wrong
	contains(msg, "not Kirigami.Theme.textColor")
}

test_t4_refuses_a_missing_colorset if {
	some msg in ts.deny with input as object.union(clean, {"colorSet": null})
	contains(msg, "colorSet")
}

test_t6_refuses_roster_drift if {
	inp := object.union(clean, {"roster_drift": [{"variant": "EL-Amber", "who": "make_taskswitch", "why": "make_taskswitch.VARIANTS does not declare it (GRID does)"}]})
	some msg in ts.deny with input as inp
	startswith(msg, "T6: EL-Amber")
}

test_t6_admits_no_drift if {
	count(ts.deny) == 0 with input as object.union(clean, {"roster_drift": []})
}

# exactly once: the package (by its id) with every not-measured fact null is
# withheld, and no rule judges a null
test_all_null_case_withheld_only if {
	inp := object.union(clean, {"root": null, "qmllint": null, "lint": null, "bindings": null, "roster_drift": null, "resolution": null})
	count(ts.deny) == 0 with input as inp
	w := ts.withheld with input as inp
	every f in ["root", "qmllint", "lint", "bindings", "roster_drift"] {
		sprintf("%s was not measured", [f]) in w
	}
}

# each population flag null on its own is withheld and not denied
test_each_flag_null_withheld if {
	every f in ["root", "qmllint", "lint", "bindings", "roster_drift"] {
		inp := object.union(clean, {f: null})
		count(ts.deny) == 0 with input as inp
		sprintf("%s was not measured", [f]) in ts.withheld with input as inp
	}
}

# N1 T0: a present id still admits past T0; a null id is still the empty-population denial
test_t0_null_id_denies if {
	some msg in ts.deny with input as object.union(clean, {"id": null, "defaults_id": null})
	startswith(msg, "T0:")
}

# N1 T2: a null root is withheld, not "the QML root is not KWin.TabBoxSwitcher"
test_null_root_not_t2 if {
	inp := object.union(clean, {"root": null})
	count(ts.deny) == 0 with input as inp
	"root was not measured" in ts.withheld with input as inp
}

# N1 W: a null qmllint is "not measured", not "qmllint is not installed"
test_null_qmllint_not_uninstalled if {
	w := ts.withheld with input as object.union(clean, {"qmllint": null})
	not "qmllint is not installed on this host; the switcher QML was not linted" in w
	"qmllint was not measured" in w
}

test_withheld_without_qmllint if {
	inp := object.union(clean, {"qmllint": false})
	count(ts.deny) == 0 with input as inp
	count(ts.withheld) == 1 with input as inp
}
