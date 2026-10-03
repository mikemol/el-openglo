package el.symmetry_test

import data.el.symmetry as p
import rego.v1

board := {"label": "marquee-field", "variant": "EL-Amber", "pip_widths": [3], "gaps": [1], "columns": 105}

grad_ok := {"label": "gradient-d0.2", "depth": 0.2, "stops": [
	{"pos": 0.0, "lit": false}, {"pos": 0.2, "lit": true}, {"pos": 0.8, "lit": true}, {"pos": 1.0, "lit": false},
]}

good := {"cases": [], "grids": [board], "gradients": [grad_ok], "noise": 12}

# W216: the lit profile is centre-fed - every stop has its mirror at 1-pos, same fade
test_y5_admits_a_centre_fed_profile if {
	count(p.deny) == 0 with input as good
}

test_y5_refuses_a_one_sided_profile if {
	one := object.union(grad_ok, {"stops": [{"pos": 0.0, "lit": false}, {"pos": 0.3, "lit": true}, {"pos": 1.0, "lit": true}]})
	some m in p.deny with input as object.union(good, {"gradients": [one]})
	startswith(m, "Y5: gradient-d0.2")
}

test_y5_refuses_a_stop_mirrored_at_the_wrong_fade if {
	skew := object.union(grad_ok, {"stops": [{"pos": 0.0, "lit": false}, {"pos": 1.0, "lit": true}]})
	some m in p.deny with input as object.union(good, {"gradients": [skew]})
	startswith(m, "Y5: gradient-d0.2")
}

test_y5_refuses_no_profile_population if {
	some m in p.deny with input as {"cases": [], "grids": [board], "gradients": []}
	startswith(m, "Y5:")
	some n in p.deny with input as {"grids": [board]}
	startswith(n, "Y5:")
}

test_y5_withholds_an_unreadable_profile if {
	g := {"label": "gradient-d0.2", "depth": 0.2, "stops": null}
	inp := object.union(good, {"gradients": [g]})
	some m in p.withheld with input as inp
	startswith(m, "W: gradient-d0.2")
	count(p.deny) == 0 with input as inp
}

test_admits_a_regular_board if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	p.admitted == {"marquee-field"} with input as good
}

# mirror regions are diagnostic: a face full of asymmetries still admits the grid
test_mirror_regions_never_deny if {
	face := {"label": "face-0000", "scope": "face", "planes": {"h": {"regions": [{"box": [0, 0, 9, 9], "pixels": 40, "worst": 200, "where": "upper-left"}], "pixels": 40}}}
	inp := object.union(good, {"cases": [face]})
	count(p.deny) == 0 with input as inp
}

fit_ok := {"fit": {"ox": 4.5, "oy": 4.5, "segLen": 50}, "residuals": {"A": 0, "B": 0}, "absent": [], "offenders": []}

glyph(f) := {"label": "glyph-8", "scope": "glyph", "planes": {}, "segment_fit": f}

# W165: a clean fit admits
test_y3_admits_a_clean_fit if {
	count(p.deny) == 0 with input as object.union(good, {"cases": [glyph(fit_ok)]})
}

test_y3_refuses_a_named_offender if {
	bad := object.union(fit_ok, {"residuals": {"A": 0, "B": 3.1}, "offenders": ["B"]})
	"Y3: glyph-8: segment B misses the substrate fit by 3.1 px" in p.deny with input as object.union(good, {"cases": [glyph(bad)]})
}

test_y4_refuses_an_absent_segment if {
	bad := object.union(fit_ok, {"absent": ["G"]})
	some m in p.deny with input as object.union(good, {"cases": [glyph(bad)]})
	startswith(m, "Y4: glyph-8")
}

test_y0_refuses_no_grid if {
	some m in p.deny with input as {"cases": [], "grids": []}
	startswith(m, "Y0:")
	some n in p.deny with input as {}
	startswith(n, "Y0:")
}

# the operator's catch, twice by eye: a fractional pitch rounded per pip
test_y2_refuses_an_uneven_pitch if {
	inp := object.union(good, {"grids": [object.union(board, {"gaps": [1, 2]})]})
	"Y2: marquee-field (EL-Amber): gaps [1, 2] — the grid is not one pitch" in p.deny with input as inp
	count(p.admitted) == 0 with input as inp
}

test_y2_refuses_uneven_pips if {
	inp := object.union(good, {"grids": [object.union(board, {"pip_widths": [2, 3]})]})
	"Y2: marquee-field (EL-Amber): pip widths [2, 3] — the pips are not one size" in p.deny with input as inp
}

# the silent pass the Python had: a blank board is "<= 1 distinct" of everything
test_y1_refuses_a_blank_board if {
	blank := object.union(board, {"pip_widths": [], "gaps": [], "columns": 0})
	inp := object.union(good, {"grids": [blank]})
	"Y1: marquee-field (EL-Amber): 0 lit column(s); a grid needs two to have a pitch" in p.deny with input as inp
	count(p.admitted) == 0 with input as inp
}

test_withholds_without_the_renderer if {
	w := {"label": "marquee-field", "variant": "EL-Amber", "withheld": "/usr/bin/qml is not installed"}
	inp := object.union(good, {"grids": [w]})
	"Y0: marquee-field (EL-Amber): /usr/bin/qml is not installed" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
	count(p.admitted) == 0 with input as inp
}

test_all_null_grid_withheld_only if {
	g := {"label": "marquee-field", "variant": "EL-Amber", "pip_widths": null, "gaps": null, "columns": null}
	inp := object.union(good, {"grids": [g]})
	"W: marquee-field: gaps was not measured" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
	count(p.admitted) == 0 with input as inp
}
