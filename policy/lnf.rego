# METADATA
# title: "L0 — no package measured admits nothing; every declared package is measured"
# description: |
#   The measurement is `scripts/check_lnf.py --json`: make_deb.VARIANTS x
#   make_deb.ENGINES staged through build_lnf_packages, each package's
#   metadata.json and contents/defaults read back, and `engines` — what the
#   packager declares each engine selects. W37.
package el.lnf

import rego.v1

deny contains "L0: no LnF package was measured; the population is empty, not the packages well-formed" if {
	count(object.get(input, "cases", [])) == 0
}

deny contains msg if {
	some c in input.cases
	c.missing != null
	msg := sprintf("L0: %s: %s", [c.id, c.missing])
}

deny contains msg if {
	some p in object.get(input, "undeclared_staged", [])
	msg := sprintf("L0: %s is staged but not declared by VARIANTS x ENGINES", [p])
}

# METADATA
# title: "L1 — the package is a LookAndFeel whose id is its directory and its own LookAndFeelPackage"
deny contains msg if {
	some c in read
	c.structure != "Plasma/LookAndFeel"
	msg := sprintf("L1: %s: KPackageStructure is %v (anything else is invisible to Plasma)", [c.id, c.structure])
}

deny contains msg if {
	some c in read
	c.meta_id != c.id
	msg := sprintf("L1: %s: metadata Id is %v", [c.id, c.meta_id])
}

deny contains msg if {
	some c in read
	c.lnf_package != c.id
	msg := sprintf("L1: %s: defaults LookAndFeelPackage is %v", [c.id, c.lnf_package])
}

# METADATA
# title: "L2 — the package applies its own variant's colour scheme"
deny contains msg if {
	some c in read
	c.color_scheme != c.variant
	msg := sprintf("L2: %s: ColorScheme is %v, not %s", [c.id, c.color_scheme, c.variant])
}

# METADATA
# title: "L3 — the package selects its engine's widget style and decoration"
deny contains msg if {
	some c in read
	want := input.engines[c.engine]
	c.widget_style != want.widget
	msg := sprintf("L3: %s: widgetStyle is %v, engine %s selects %s", [c.id, c.widget_style, c.engine, want.widget])
}

deny contains msg if {
	some c in read
	want := input.engines[c.engine]
	c.deco_library != want.deco_library
	msg := sprintf("L3: %s: decoration library is %v, engine %s selects %s", [c.id, c.deco_library, c.engine, want.deco_library])
}

deny contains msg if {
	some c in read
	want := input.engines[c.engine]
	want.deco_theme != (object.get(c, "deco_theme", null) != null)
	msg := sprintf("L3: %s: decoration theme %v disagrees with engine %s (theme expected: %v)", [c.id, object.get(c, "deco_theme", null), c.engine, want.deco_theme])
}

withheld contains msg if {
	some c in input.cases
	not "missing" in object.keys(c)
	msg := sprintf("L0: %v: missing was not measured", [object.get(c, "id", null)])
}

read contains c if {
	some c in input.cases
	"missing" in object.keys(c)
	c.missing == null
}

admitted contains c.id if {
	some c in read
	want := input.engines[c.engine]
	c.structure == "Plasma/LookAndFeel"
	c.meta_id == c.id
	c.lnf_package == c.id
	c.color_scheme == c.variant
	c.widget_style == want.widget
	c.deco_library == want.deco_library
}
