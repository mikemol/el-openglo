package el.inherit_test

import data.el.inherit as p
import rego.v1

off := {"id": "EL-Openglo", "icon_parents": ["breeze-dark", "hicolor"], "cursor_parent": "breeze_cursors_light", "icon_dirs": ["scalable"], "defaults_ok": true, "missing": null, "installed": {"breeze-dark": true, "breeze_cursors_light": true}}

lit := {"id": "EL-Openglo-Lit", "icon_parents": ["breeze", "hicolor"], "cursor_parent": "breeze_cursors", "icon_dirs": ["scalable"], "defaults_ok": true, "missing": null, "installed": {"breeze": true, "breeze_cursors": true}}

good := {"roster": ["EL-Openglo", "EL-Openglo-Lit"], "cases": [off, lit]}

test_admits_well_formed_themes if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	p.admitted == {"EL-Openglo", "EL-Openglo-Lit"} with input as good
}

test_i0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "I0:")
}

# the real W65 failure (probe inherit/variant-roster): make_inherit.VARIANTS short
# one variant took the old check from "6 of 6" to "5 of 5", exit 0
test_i0_refuses_a_variant_the_emitter_dropped if {
	why := "declared by make_schemes.GRID but make_inherit.VARIANTS does not emit it"
	bad := object.union(good, {"cases": [off, {"id": "EL-Openglo-Lit", "missing": why}]})
	some msg in p.deny with input as bad
	msg == sprintf("I0: EL-Openglo-Lit: %s", [why])
	p.admitted == {"EL-Openglo"} with input as bad
}

test_i0_refuses_a_declared_variant_not_measured_at_all if {
	some msg in p.deny with input as object.union(good, {"cases": [off]})
	msg == "I0: EL-Openglo-Lit: declared but not measured"
}

test_i1_refuses_a_chain_without_hicolor if {
	bad := object.union(good, {"cases": [object.union(off, {"icon_parents": ["breeze-dark"]}), lit]})
	some msg in p.deny with input as bad
	startswith(msg, "I1: EL-Openglo: icon Inherits does not end in hicolor")
}

test_i1_refuses_a_swapped_polarity if {
	bad := object.union(good, {"cases": [object.union(off, {"icon_parents": ["breeze", "hicolor"]}), lit]})
	some msg in p.deny with input as bad
	msg == "I1: EL-Openglo: an Off variant inherits breeze-dark and a Lit one breeze; got breeze"
}

test_i2_refuses_no_directories if {
	some msg in p.deny with input as object.union(good, {"cases": [object.union(off, {"icon_dirs": []}), lit]})
	msg == "I2: EL-Openglo: the icon theme declares no Directories"
}

test_i3_refuses_no_cursor_parent if {
	some msg in p.deny with input as object.union(good, {"cases": [object.union(off, {"cursor_parent": ""}), lit]})
	msg == "I3: EL-Openglo: the cursor theme names no parent"
}

test_i4_refuses_defaults_that_select_another_theme if {
	some msg in p.deny with input as object.union(good, {"cases": [object.union(off, {"defaults_ok": false}), lit]})
	msg == "I4: EL-Openglo: the LnF defaults do not select the emitted theme names"
}

# Breeze not installed is a fact about the host: withheld, and a SKIP beside admitted cases
test_i5_an_uninstalled_parent_is_withheld_not_denied if {
	bare := object.union(good, {"cases": [object.union(off, {"installed": {"breeze-dark": false, "breeze_cursors_light": false}}), lit]})
	count(p.deny) == 0 with input as bare
	count(p.withheld) == 2 with input as bare
	count(p.admitted) == 2 with input as bare
}
