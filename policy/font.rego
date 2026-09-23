# METADATA
# title: "F0 — no fonts measured admits nothing"
# description: |
#   The measurement is `scripts/check_font.py --json`: one case per
#   make_font.OUTPUTS entry. A TTF case carries the required tables it lacks,
#   the charset code points its cmap lacks, the glyphs whose contour count
#   differs from the substrate's lit primitives, the glyphs the orientation gate
#   reports flipped against the SOURCE contours (the SPEC-FLIP class), the blank
#   glyphs with ink, the glyphs reaching below the baseline beside the declared
#   descenders, and (5x8) the descent metrics. An SVG case carries its parse
#   error or the members it lacks / carries beyond the charset. fontTools absent
#   withholds. Weakness: fontconfig and a shaper are not run.
package el.font

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	object.get(input, "withheld", null) == null
	msg := "F0: no fonts were measured; the search is broken, not the fonts sound"
}

# ⚑ `input.withheld` ALONE IS NOT A TEST: rego's null is truthy (only false
# fails a body), so a measured `"withheld": null` would withhold
withheld contains msg if {
	object.get(input, "withheld", null) != null
	msg := sprintf("F0: %s", [input.withheld])
}

ttf contains c if {
	some c in input.cases
	c.kind == "ttf"
}

svg contains c if {
	some c in input.cases
	c.kind == "svg"
}

# METADATA
# title: "F1 — a TTF carries the tables a TrueType font needs"
deny contains msg if {
	some c in ttf
	count(c.tables_missing) > 0
	msg := sprintf("F1: %s: missing tables %v", [c.id, c.tables_missing])
}

# METADATA
# title: "F2 — the cmap round-trips the whole charset plus space"
deny contains msg if {
	some c in ttf
	count(c.cmap_missing) > 0
	msg := sprintf("F2: %s: cmap lacks %v", [c.id, c.cmap_missing])
}

# METADATA
# title: "F3 — a glyph is the union of its lit primitives, no more, no less"
deny contains msg if {
	some c in ttf
	some g in c.contour_mismatch
	msg := sprintf("F3: %s: %s has %d contours, the substrate lights %d", [c.id, g.glyph, g.contours, g.primitives])
}

# METADATA
# title: "F4 — the built glyph sits on the same side as its source (SPEC-FLIP)"
deny contains msg if {
	some c in ttf
	count(c.flipped) > 0
	msg := sprintf("F4: %s: flipped against the source: %v", [c.id, c.flipped])
}

# METADATA
# title: "F5 — space and .notdef are empty"
deny contains msg if {
	some c in ttf
	count(c.blank_inked) > 0
	msg := sprintf("F5: %s: blank glyph(s) carry ink: %v", [c.id, c.blank_inked])
}

# METADATA
# title: "F6 — only descenders reach below the baseline, and every descender does"
deny contains msg if {
	some c in ttf
	extra := {g | some g in c.below_baseline} - {g | some g in c.descenders}
	count(extra) > 0
	msg := sprintf("F6: %s: non-descenders below the baseline: %v", [c.id, sort(extra)])
}

deny contains msg if {
	some c in ttf
	short := {g | some g in c.descenders} - {g | some g in c.below_baseline}
	count(short) > 0
	msg := sprintf("F6: %s: descenders not below the baseline: %v", [c.id, sort(short)])
}

# METADATA
# title: "F7 — a baseline font declares a negative descent"
deny contains msg if {
	some c in ttf
	c.descent != null
	not negative_descent(c.descent)
	msg := sprintf("F7: %s: descent metrics are not negative (hhea %v, OS/2 %v)", [c.id, c.descent.hhea, c.descent.os2])
}

negative_descent(d) if {
	d.hhea < 0
	d.os2 < 0
}

# METADATA
# title: "F8 — an SVG font parses, with one glyph per charset member"
deny contains msg if {
	some c in svg
	c.parse_error != null
	msg := sprintf("F8: %s: does not parse: %s", [c.id, c.parse_error])
}

deny contains msg if {
	some c in svg
	c.parse_error == null
	count(c.missing) + count(c.extra) > 0
	msg := sprintf("F8: %s: missing %v extra %v", [c.id, c.missing, c.extra])
}

admitted contains c.id if {
	some c in ttf
	count(c.tables_missing) + count(c.cmap_missing) + count(c.contour_mismatch) + count(c.flipped) + count(c.blank_inked) == 0
	{g | some g in c.below_baseline} == {g | some g in c.descenders}
	descent_ok(c)
}

admitted contains c.id if {
	some c in svg
	c.parse_error == null
	count(c.missing) + count(c.extra) == 0
}

descent_ok(c) if c.descent == null

descent_ok(c) if negative_descent(c.descent)
