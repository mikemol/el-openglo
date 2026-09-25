package el.kerning

# W76 — adjacent letters never bleed into one another through the pip mask. The
# measurement is scripts/check_kerning.py --json: two stills of the real widget (the
# same body plain and bold), read back as pip grids; per view and style, the widths
# of the runs of lit columns between fully dark ones. ⚑ Operator ruling 2026-09-25:
# kerning is a CLOSED LOOP — a pair is pushed apart only while it bleeds — so this
# judges the pixels, never the widget's offsets.

import rego.v1

# first rule: an ABSENT or empty population is a broken search, not a clean board
deny contains "K0: no view measured: the search is broken" if {
	count(object.get(input, "cases", [])) == 0
	count(object.get(input, "withheld", [])) == 0
}

# BLOOM — THE MODEL'S, not a tuning: bold's grow = s/2 overhangs by at most one pip
# column (measured 2026-09-25: regular runs 5 = glyph_cols, bold 6), so one letter's
# footprint is at most glyph_cols + 1. Two letters merged read ~2 x glyph_cols.
bloom := 1

# K1 — an interior run wider than one letter + its bloom: two letters bled together
deny contains msg if {
	some c in object.get(input, "cases", [])
	some i, w in object.get(c, "interior_runs", [])
	w > c.glyph_cols + bloom
	msg := sprintf("K1: %s %s under %s: interior run %d is %d columns, wider than a %d-column glyph + %d bloom: letters bleed together",
		[c.variant, c.style, c.view, i, w, c.glyph_cols, bloom])
}

# K2 — a case with no interior run judged nothing (text too short, or unreadable)
deny contains msg if {
	some c in object.get(input, "cases", [])
	count(object.get(c, "interior_runs", [])) == 0
	msg := sprintf("K2: %s %s under %s: no interior run to judge", [c.variant, c.style, c.view])
}

# K3 — both styles measured: bold is where the bloom overhangs, so a regular-only
# measurement never tested the loop
deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	some s in ["regular", "bold"]
	count([c | some c in input.cases; c.style == s]) == 0
	msg := sprintf("K3: no %s view measured", [s])
}

admitted contains sprintf("%s/%s/%s", [c.variant, c.style, c.view]) if {
	some c in object.get(input, "cases", [])
	count(object.get(c, "interior_runs", [])) > 0
	every w in c.interior_runs { w <= c.glyph_cols + bloom }
}

withheld contains msg if {
	some w in object.get(input, "withheld", [])
	msg := sprintf("%s: %s", [w.variant, w.reason])
}
