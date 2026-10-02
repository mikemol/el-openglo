package el.lnf_test

import rego.v1

import data.el.lnf

engines := {
	"breeze": {"widget": "Breeze", "deco_library": "org.kde.kwin.aurorae", "deco_theme": true},
	"oxygen": {"widget": "oxygen", "deco_library": "org.kde.oxygen", "deco_theme": false},
}

good_breeze := {
	"id": "org.el.openglo.elazure", "variant": "EL-Azure", "engine": "breeze", "missing": null,
	"meta_id": "org.el.openglo.elazure", "structure": "Plasma/LookAndFeel",
	"color_scheme": "EL-Azure", "widget_style": "Breeze", "lnf_package": "org.el.openglo.elazure",
	"deco_library": "org.kde.kwin.aurorae", "deco_theme": "__aurorae__svg__EL-Azure",
}

good_oxygen := {
	"id": "org.el.openglo.elazureoxygen", "variant": "EL-Azure", "engine": "oxygen", "missing": null,
	"meta_id": "org.el.openglo.elazureoxygen", "structure": "Plasma/LookAndFeel",
	"color_scheme": "EL-Azure", "widget_style": "oxygen", "lnf_package": "org.el.openglo.elazureoxygen",
	"deco_library": "org.kde.oxygen", "deco_theme": null,
}

doc(cases) := {"engines": engines, "cases": cases, "undeclared_staged": []}

test_admits_both_engines if {
	count(lnf.deny) == 0 with input as doc([good_breeze, good_oxygen])
	count(lnf.admitted) == 2 with input as doc([good_breeze, good_oxygen])
}

test_empty_population_denied if {
	"L0: no LnF package was measured; the population is empty, not the packages well-formed" in lnf.deny with input as {}
}

test_missing_package_denied if {
	some m in lnf.deny with input as doc([object.union(good_oxygen, {"missing": "declared but not staged"})])
	startswith(m, "L0: org.el.openglo.elazureoxygen")
}

test_undeclared_staged_denied if {
	some m in lnf.deny with input as object.union(doc([good_breeze]), {"undeclared_staged": ["org.el.stray"]})
	contains(m, "org.el.stray")
}

test_oxygen_with_breeze_style_denied if {
	some m in lnf.deny with input as doc([object.union(good_oxygen, {"widget_style": "Breeze"})])
	startswith(m, "L3:")
}

test_oxygen_with_aurorae_theme_denied if {
	some m in lnf.deny with input as doc([object.union(good_oxygen, {"deco_theme": "__aurorae__svg__EL-Azure"})])
	startswith(m, "L3:")
}

test_wrong_scheme_denied if {
	some m in lnf.deny with input as doc([object.union(good_breeze, {"color_scheme": "BreezeLight"})])
	startswith(m, "L2:")
}

test_id_mismatch_denied if {
	some m in lnf.deny with input as doc([object.union(good_breeze, {"lnf_package": "org.kde.breeze"})])
	startswith(m, "L1:")
}

test_unmeasured_case_withheld if {
	count(lnf.withheld) == 1 with input as doc([{"id": "x", "variant": "EL-Azure", "engine": "breeze"}])
}
