# METADATA
# title: "T0 — an unmeasured package admits nothing"
# description: |
#   The measurement is `scripts/check_taskswitch.py --json`: ONE emitted
#   KWin/WindowSwitcher package (⊕ONE-THEME, W35 — the variant is the active
#   colour scheme, not a package).
package el.taskswitch

import rego.v1

deny contains msg if {
	not input.id
	msg := "T0: no switcher package was measured (no id)"
}

# METADATA
# title: "T1 — the package is what KWin loads: structure, and the id the LnF defaults name"
# description: |
#   KWin loads by KPackageStructure and by [kwinrc][TabBox] LayoutName; an id
#   the defaults do not name is a stock switcher in silence.
deny contains msg if {
	input.structure != "KWin/WindowSwitcher"
	msg := sprintf("T1: KPackageStructure is %v, not KWin/WindowSwitcher", [input.structure])
}

deny contains msg if {
	input.id != input.defaults_id
	msg := sprintf("T1: the LnF defaults name %v but the package id is %v", [input.defaults_id, input.id])
}

# METADATA
# title: "T2 — the QML root is KWin.TabBoxSwitcher and the document lints"
deny contains msg if {
	not input.root
	msg := "T2: the QML root is not KWin.TabBoxSwitcher"
}

deny contains msg if {
	some d in input.lint
	msg := sprintf("T2: %s", [d])
}

# METADATA
# title: "T3 — the ghost alpha is baked, in (0,1)"
# description: |
#   The one colour fact that is not a KColorScheme role; global across the
#   variants (W23), so a single package may carry it as a constant.
deny contains msg if {
	not alpha_ok(input.alpha)
	msg := sprintf("T3: ghostAlpha is %v", [input.alpha])
}

alpha_ok(a) if {
	a > 0.0
	a < 1.0
}

# METADATA
# title: "T4 — every colour is BOUND to its scheme role under the View set, never baked"
# description: |
#   catalog/one-theme.md: lit is ForegroundNormal (Kirigami.Theme.textColor),
#   ghost is ForegroundInactive (disabledTextColor), void is [Colors:View]
#   BackgroundNormal (backgroundColor), under colorSet View — the roles
#   make_schemes.emit_colors writes the fg / fg_in / view tokens into. A baked
#   hex would not follow plasma-apply-colorscheme; a wrong role would follow
#   the wrong token; a missing colorSet reads the Window set's colours.
deny contains msg if {
	some hole, role in input.roles
	bound := input.bindings[hole]
	bound != sprintf("Kirigami.Theme.%s", [role])
	msg := sprintf("T4: %s is %v, not Kirigami.Theme.%s", [hole, bound, role])
}

deny contains msg if {
	input.colorSet != "View"
	msg := sprintf("T4: Kirigami.Theme.colorSet is %v, not View", [input.colorSet])
}

# METADATA
# title: "W — qmllint is absent, so T2's lint arm measured nothing"
withheld contains msg if {
	not input.qmllint
	msg := "qmllint is not installed on this host; the switcher QML was not linted"
}
