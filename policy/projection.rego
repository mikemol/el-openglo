# METADATA
# title: "V0 — a font was found and the authored table was projected"
# description: |
#   The measurement is `scripts/check_projection.py --json`: the TTF found (null
#   when none), the format and frame, and per authored glyph its authored and
#   projected segment sets with their jaccard (glyph_match.validate_projection).
#   ⚑ AGREEMENT IS REPORTED, NOT GATED — the threshold is ⊕SEG-PROJECT-CALIBRATE's.
#   What IS gated is that the instrument works: it ran over the table and it
#   discriminates between glyphs.
package el.projection

import rego.v1

withheld contains "V0: no TTF was found on this host; 0 authored glyphs projected" if {
	input.font == null
}

withheld contains "V0: font was not measured" if {
	not "font" in object.keys(input)
}

deny contains "V0: a font was found but the authored table projected to nothing; nothing was validated" if {
	is_string(input.font)
	count(object.get(input, "glyphs", [])) == 0
}

# METADATA
# title: "V1 — the matcher discriminates: at least half the glyphs project distinctly"
# description: |
#   A matcher that projects every glyph to the same set (dead ink, a broken
#   frame) still "runs". The distinct projections must be at least half the glyphs.
distinct := {sort(g.projected) | some g in input.glyphs}

deny contains msg if {
	is_string(input.font)
	n := count(input.glyphs)
	n > 0
	count(distinct) < floor(n / 2)
	msg := sprintf("V1: only %d distinct projection(s) over %d glyphs; the matcher is not seeing the ink", [count(distinct), n])
}

withheld contains msg if {
	is_string(input.font)
	some g in object.get(input, "glyphs", [])
	not is_array(object.get(g, "projected", null))
	msg := sprintf("W: glyph %v: projected was not measured", [object.get(g, "ch", null)])
}

admitted contains "projection" if {
	is_string(input.font)
	count(input.glyphs) > 0
	count(deny) == 0
	every g in input.glyphs {
		is_array(object.get(g, "projected", null))
	}
}
