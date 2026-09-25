package el.gtk_test

import data.el.gtk as p
import rego.v1

pair := {"bg": "--window-bg-color", "fg": "--window-fg-color", "floor": 4.5, "present": true, "ratio": 12.3}

case := {"id": "EL-Openglo", "parse_errors": 0, "unknown_gtk4": [], "unknown_gtk3": [], "wrong_values": [], "pairs": [pair]}

good := {"roster": ["EL-Openglo"], "pairs_declared": 1, "roster_drift": [], "cases": [case]}

one(c) := object.union(good, {"cases": [c]})

test_admits_clean_sheets if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	p.admitted == {"EL-Openglo"} with input as good
}

test_k0_refuses_an_absent_population if {
	some m in p.deny with input as {}
	startswith(m, "K0: no sheets")
}

test_k0_refuses_emitter_drift if {
	"K0: EL-Amber: in GRID, not in make_gtk.VARIANTS" in p.deny with input as object.union(good, {"roster_drift": [{"variant": "EL-Amber", "why": "in GRID, not in make_gtk.VARIANTS"}]})
}

# W65: a shrunk pair population is denied, not read as fewer pairs passing
test_k0_refuses_a_shrunk_pair_population if {
	"K0: EL-Openglo: 1 pair(s) measured of 8 declared" in p.deny with input as object.union(good, {"pairs_declared": 8})
}

test_k1_refuses_a_parse_error if {
	"K1: EL-Openglo: 2 parse error(s)" in p.deny with input as one(object.union(case, {"parse_errors": 2}))
}

test_k1_withholds_without_tinycss2 if {
	inp := one(object.union(case, {"parse_errors": null}))
	"K1: EL-Openglo: tinycss2 is not installed here; the parse is unmeasured" in p.withheld with input as inp
	p.admitted == {"EL-Openglo"} with input as inp
}

# session 14's hole: a typo'd name parses and silently does nothing
test_k2_refuses_a_typod_variable if {
	"K2: EL-Openglo: gtk4.css sets undocumented libadwaita variable(s) [\"--headerbar-bg-colour\"]" in p.deny with input as one(object.union(case, {"unknown_gtk4": ["--headerbar-bg-colour"]}))
}

test_k2_refuses_a_typod_define if {
	"K2: EL-Openglo: gtk3.css defines unknown colour(s) [\"theme_bg_colour\"]" in p.deny with input as one(object.union(case, {"unknown_gtk3": ["theme_bg_colour"]}))
}

test_k3_refuses_an_authored_value if {
	w := {"name": "--view-fg-color", "role": "view_fg", "got": "#00ffffff", "want": "#ffffff"}
	some m in p.deny with input as one(object.union(case, {"wrong_values": [w]}))
	startswith(m, "K3: EL-Openglo: --view-fg-color = #00ffffff, not its role view_fg")
}

test_k4_refuses_an_absent_pair if {
	gone := object.union(pair, {"present": false, "ratio": null})
	"K4: EL-Openglo: --window-fg-color on --window-bg-color: pair absent from gtk4.css" in p.deny with input as one(object.union(case, {"pairs": [gone]}))
}

test_k4_refuses_a_pair_under_its_floor if {
	low := object.union(pair, {"ratio": 1})
	"K4: EL-Openglo: --window-fg-color on --window-bg-color is 1.00:1, under 4.50:1" in p.deny with input as one(object.union(case, {"pairs": [low]}))
}

test_k4_admits_a_selection_pair_at_its_own_floor if {
	sel := {"bg": "--accent-bg-color", "fg": "--accent-fg-color", "floor": 3, "present": true, "ratio": 4.41}
	inp := one(object.union(case, {"pairs": [sel]}))
	count(p.deny) == 0 with input as inp
}

test_all_null_case_withheld_only if {
	c := {"id": "EL-Openglo", "parse_errors": null, "unknown_gtk4": null, "unknown_gtk3": null, "wrong_values": null, "pairs": [{"bg": "--x-bg", "fg": "--x-fg", "floor": 4.5, "present": null, "ratio": null}]}
	inp := one(c)
	w := p.withheld with input as inp
	"W: EL-Openglo: unknown_gtk4 was not measured" in w
	"W: EL-Openglo: pair --x-fg present was not measured" in w
	count(p.deny) == 0 with input as inp
	count(p.admitted) == 0 with input as inp
}

test_denial_does_not_leak_across_prefixed_ids if {
	lit := object.union(case, {"id": "EL-Openglo-Lit", "parse_errors": 3})
	inp := object.union(good, {"roster": ["EL-Openglo", "EL-Openglo-Lit"], "cases": [case, lit]})
	p.admitted == {"EL-Openglo"} with input as inp
}
