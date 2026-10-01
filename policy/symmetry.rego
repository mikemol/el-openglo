# METADATA
# title: "Y0 — a matrix grid was measured"
# description: |
#   The measurement is `scripts/check_symmetry.py --json`: per segment case (glyph
#   and face renders) the located mirror asymmetries, and per matrix board (W59:
#   its pips are hardware on one pitch) the distinct pip-column widths, the
#   distinct gaps between them, and the column count, read from the board's own
#   render. ⚑ THE MIRROR REGIONS ARE DIAGNOSTIC (operator, 2026-09-22: "we don't
#   expect it to match exactly — we expect it to fix defects"), so no rule here
#   judges them; `check_symmetry.py --list` reports them. The GRID is the claim.
package el.symmetry

import rego.v1

deny contains "Y0: no matrix grid was measured; the roster is empty, not the grid regular" if {
	count(object.get(input, "grids", [])) == 0
}

# METADATA
# title: "Y1 — a board shows enough columns to have a pitch at all"
# description: |
#   A blank board has no widths and no gaps, which a "<= 1 distinct" test reads as
#   regular. Two columns are the least that have a gap between them.
deny contains msg if {
	some g in input.grids
	not is_string(object.get(g, "withheld", null))
	is_number(g.columns)
	g.columns < 2
	msg := sprintf("Y1: %s (%s): %d lit column(s); a grid needs two to have a pitch", [g.label, g.variant, g.columns])
}

# METADATA
# title: "Y2 — every pip is one width and every gap one pitch"
deny contains msg if {
	some g in input.grids
	not is_string(object.get(g, "withheld", null))
	is_array(g.pip_widths)
	count(g.pip_widths) > 1
	msg := sprintf("Y2: %s (%s): pip widths %v — the pips are not one size", [g.label, g.variant, g.pip_widths])
}

deny contains msg if {
	some g in input.grids
	not is_string(object.get(g, "withheld", null))
	is_array(g.gaps)
	count(g.gaps) > 1
	msg := sprintf("Y2: %s (%s): gaps %v — the grid is not one pitch", [g.label, g.variant, g.gaps])
}

# METADATA
# title: "Y3 — every rendered segment sits on the substrate's coordinates"
# description: |
#   W165: the glyph-8 render's segments are fitted by least squares to the
#   substrate's unit coordinates (cx = ox + L·a, cy = oy + L·b). Unlike a mirror
#   region this is not diagnostic: an offender is a NAMED segment whose centroid
#   misses the fit by more than a pixel, which no symmetric-in-both-planes defect
#   can hide from.
deny contains msg if {
	some c in object.get(input, "cases", [])
	f := object.get(c, "segment_fit", null)
	is_object(f)
	some s in object.get(f, "offenders", [])
	msg := sprintf("Y3: %s: segment %s misses the substrate fit by %v px", [c.label, s, f.residuals[s]])
}

# METADATA
# title: "Y4 — an all-lit glyph shows every segment"
deny contains msg if {
	some c in object.get(input, "cases", [])
	f := object.get(c, "segment_fit", null)
	is_object(f)
	count(object.get(f, "absent", [])) > 0
	msg := sprintf("Y4: %s: segment(s) %v absent from an all-lit render", [c.label, f.absent])
}

withheld contains msg if {
	some g in input.grids
	is_string(object.get(g, "withheld", null))
	msg := sprintf("Y0: %s (%s): %s", [g.label, g.variant, g.withheld])
}

withheld contains msg if {
	some g in input.grids
	not is_string(object.get(g, "withheld", null))
	some k in ["pip_widths", "gaps", "columns"]
	object.get(g, k, null) == null
	msg := sprintf("W: %s: %s was not measured", [g.label, k])
}

denied_labels contains g.label if {
	some g in input.grids
	some m in deny
	contains(m, sprintf(": %s (", [g.label]))
}

admitted contains g.label if {
	some g in input.grids
	not is_string(object.get(g, "withheld", null))
	every k in ["pip_widths", "gaps", "columns"] {
		object.get(g, k, null) != null
	}
	not g.label in denied_labels
}
