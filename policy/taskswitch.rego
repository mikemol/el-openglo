# METADATA
# title: "T0 — an unmeasured package admits nothing"
# description: |
#   The measurement is `scripts/check_taskswitch.py --json`: ONE emitted
#   KWin/WindowSwitcher package (⊕ONE-THEME, W35 — the variant is the active
#   colour scheme, not a package).
package el.taskswitch

import rego.v1

import data.el.truth

# `id` is a string (or None when the metadata carries no Id): null, absent and
# "" all mean no package id, and this is the empty-population denial.
deny contains msg if {
	not truth.py(object.get(input, "id", null))
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
	input.root == false
	msg := "T2: the QML root is not KWin.TabBoxSwitcher"
}

# METADATA
# title: "W — a fact the measurement always emits, null or absent, judges nothing"
# description: |
#   check_taskswitch always emits root (bool), qmllint (bool), lint (list),
#   bindings (object) and roster_drift (list). Null or absent means it could
#   not say, so the rule that reads it is withheld, not silently passed.
#   structure / defaults_id / colorSet / alpha are NOT here: the measurement
#   emits None for them when the line is missing from the emitted package, a
#   measured absence the T1 / T3 / T4 rules deny.
withheld contains msg if {
	some f, want in {"root": "boolean", "qmllint": "boolean", "lint": "array", "bindings": "object", "roster_drift": "array"}
	type_name(object.get(input, f, null)) != want
	msg := sprintf("%s was not measured", [f])
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
# title: "T5 — the bindings RESOLVE to each variant's tokens under the real Kirigami.Theme"
# description: |
#   theme_probe runs the emitted binding lines under a private kdeglobals that
#   IS the variant's .colors, with the KDE platform theme and Kirigami's
#   org.kde.desktop platform plugin: what a bound switcher draws when that
#   scheme is applied. Each variant's resolved lit / ghost / void must equal
#   the tokens the palette solved (fg / fg_in / view). This is the "follows
#   plasma-apply-colorscheme" probe, headless.
deny contains msg if {
	some v, r in input.resolution
	some hole, got in r.resolved
	got != r.expected[hole]
	msg := sprintf("T5: under %s, %s resolves to %s, not the variant's %s", [v, hole, got, r.expected[hole]])
}

# METADATA
# title: "T6 — make_taskswitch's own VARIANTS is the roster (make_schemes.GRID)"
# description: |
#   T5 resolves over the ROSTER, never the emitter's list; an emitter that drops
#   or invents a variant is a deny, not a quietly narrower T5 (W61 R1).
deny contains msg if {
	some d in object.get(input, "roster_drift", [])
	msg := sprintf("T6: %s %s", [d.variant, d.why])
}

# METADATA
# title: "W — qmllint is absent, so T2's lint arm measured nothing"
withheld contains msg if {
	input.qmllint == false
	msg := "qmllint is not installed on this host; the switcher QML was not linted"
}

withheld contains msg if {
	object.get(input, "resolution", null) == null
	msg := "the qml runner or the .colors files are absent; the bindings were not resolved (T5)"
}
