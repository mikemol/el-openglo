package el.symmetry_test

import data.el.symmetry as p
import rego.v1

board := {"label": "marquee-field", "variant": "EL-Amber", "pip_widths": [3], "gaps": [1], "columns": 105}

good := {"cases": [], "grids": [board], "noise": 12}

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
