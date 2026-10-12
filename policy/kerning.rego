package el.kerning

# W76 — adjacent letters never bleed into one another through the pip mask. The
# measurement is scripts/check_kerning.py --json: the same body text plain and bold run
# through the real widget's STEPPED capture, a sweep of frames read back as pip grids; per
# view and style, the widest interior stroke group (columns whose brightest ink is at least
# 0.6 of the still's peak) over the sweep. ⚑ Operator ruling 2026-09-25: kerning is a CLOSED
# LOOP — a pair is pushed apart only while it bleeds — so this judges the pixels, never the
# widget's offsets.
#
# ⚑ K1 (a binary lit-run on one moment-grab still) AND ITS POPULATION GUARDS K2 AND K3 ARE RETIRED
# (W529, W527). The still was taken at the first sample with the text mid-board, so the scroll
# phase depended on frame timing, and at a half-pip phase the colour-vision views' per-still
# threshold fused the whole text into an 18 to 45 column run: a verdict that could change between
# two runs of the same tree. The stroke group is graded, reads the same in every view at every
# phase, and catches the same defect (measured: with the kern loop disabled both denied, in all
# four views, at a 30-column group). K4 is that rule; K0, K5 and K6 are the population guards.

import rego.v1

# first rule: an ABSENT or empty population is a broken search, not a clean board
deny contains "K0: no view measured: the search is broken" if {
	count(object.get(input, "gaps", [])) == 0
	count(object.get(input, "withheld", [])) == 0
}

# BLOOM — THE MODEL'S, not a tuning: bold's grow = s/2 overhangs by at most one pip
# column (measured: regular groups 4 or 5 = glyph_cols, bold 5 or 6), so one letter's
# footprint is at most glyph_cols + 1. Two letters fused read ~2 x glyph_cols.
bloom := 1

# a phase cycle is the 0.618-pip step: fewer frames than this met too few phases
min_sweep := 6

# K4 — a stroke group wider than one letter + its bloom at SOME scroll phase: two letters fused there
deny contains msg if {
	some g in object.get(input, "gaps", [])
	g.max_group > g.glyph_cols + bloom
	msg := sprintf("K4: %s %s under %s: over %d stepped frames the widest stroke group is %d columns, wider than a %d-column glyph + %d bloom: letters fuse at some scroll phase",
		[g.variant, g.style, g.view, g.frames, g.max_group, g.glyph_cols, bloom])
}

# K5 — both styles swept: bold is where the bloom overhangs, so a regular-only sweep never tested the loop
deny contains msg if {
	count(object.get(input, "gaps", [])) > 0
	some s in ["regular", "bold"]
	count([g | some g in input.gaps; g.style == s]) == 0
	msg := sprintf("K5: no %s sweep measured", [s])
}

# K6 — a sweep shorter than a phase cycle judged almost nothing
deny contains msg if {
	some g in object.get(input, "gaps", [])
	g.frames < min_sweep
	msg := sprintf("K6: %s %s under %s: only %d stepped frames read, fewer than the %d a phase sweep needs",
		[g.variant, g.style, g.view, g.frames, min_sweep])
}

admitted contains sprintf("%s/%s/%s", [g.variant, g.style, g.view]) if {
	some g in object.get(input, "gaps", [])
	g.max_group <= g.glyph_cols + bloom
	g.frames >= min_sweep
}

withheld contains msg if {
	some w in object.get(input, "withheld", [])
	msg := sprintf("%s: %s", [w.variant, w.reason])
}
