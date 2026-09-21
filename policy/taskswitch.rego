# METADATA
# title: "T0 — no variants measured admits nothing"
# description: |
#   The measurement is `scripts/check_taskswitch.py --json`, one record per
#   emitted KWin/WindowSwitcher package.
package el.taskswitch

import rego.v1

deny contains msg if {
	count(input.variants) == 0
	msg := "T0: no switcher packages were measured"
}

# METADATA
# title: "T1 — the package is what KWin loads: structure, and the id the LnF defaults name"
# description: |
#   KWin loads by KPackageStructure and by [kwinrc][TabBox] LayoutName; an id
#   the defaults do not name is a stock switcher in silence.
deny contains msg if {
	some v in input.variants
	v.structure != "KWin/WindowSwitcher"
	msg := sprintf("T1: %s: KPackageStructure is %v, not KWin/WindowSwitcher", [v.variant, v.structure])
}

deny contains msg if {
	some v in input.variants
	v.id != v.defaults_id
	msg := sprintf("T1: %s: the LnF defaults name %v but the package id is %v", [v.variant, v.defaults_id, v.id])
}

deny contains msg if {
	some v in input.variants
	not v.id
	msg := sprintf("T1: %s: the package has no id", [v.variant])
}

# METADATA
# title: "T2 — the QML root is KWin.TabBoxSwitcher and the document lints"
deny contains msg if {
	some v in input.variants
	not v.root
	msg := sprintf("T2: %s: the QML root is not KWin.TabBoxSwitcher", [v.variant])
}

deny contains msg if {
	some v in input.variants
	some d in v.lint
	msg := sprintf("T2: %s: %s", [v.variant, d])
}

# METADATA
# title: "T3 — the colour holes are filled from the variant, distinct, with the solved ghost alpha"
deny contains msg if {
	some v in input.variants
	some k, c in v.colors
	c == null
	msg := sprintf("T3: %s: the %s hole is unfilled", [v.variant, k])
}

deny contains msg if {
	some v in input.variants
	not null in {c | some _, c in v.colors}
	count({c | some _, c in v.colors}) < 3
	msg := sprintf("T3: %s: lit/ghost/void are not distinct (%v)", [v.variant, v.colors])
}

deny contains msg if {
	some v in input.variants
	not alpha_ok(v.alpha)
	msg := sprintf("T3: %s: ghostAlpha is %v", [v.variant, v.alpha])
}

alpha_ok(a) if {
	a > 0.0
	a < 1.0
}

# METADATA
# title: "W — qmllint is absent, so T2's lint arm measured nothing"
withheld contains msg if {
	not input.qmllint
	msg := "qmllint is not installed on this host; the switcher QML was not linted"
}
