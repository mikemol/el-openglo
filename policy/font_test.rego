package el.font_test

import data.el.font as p
import rego.v1

ttf(id) := {"kind": "ttf", "id": id, "font": id, "charset": "0123", "tables_missing": [], "cmap_missing": [], "contour_mismatch": [], "flipped": [], "blank_inked": [], "below_baseline": [], "descenders": [], "descent": null}

m58 := object.union(ttf("EL-Matrix-5x8.ttf"), {"below_baseline": ["g", "j", "p", "q", "y"], "descenders": ["g", "j", "p", "q", "y"], "descent": {"hhea": -125, "os2": -125}})

svg := {"kind": "svg", "id": "EL-Segment-7.svg", "font": "EL-Segment-7.svg", "parse_error": null, "missing": [], "extra": []}

good := {"withheld": null, "cases": [ttf("EL-Segment-7.ttf"), m58, svg]}

with_case(c) := {"withheld": null, "cases": [c]}

test_admits_sound_fonts if {
	count(p.deny) == 0 with input as good
	p.admitted == {"EL-Segment-7.ttf", "EL-Matrix-5x8.ttf", "EL-Segment-7.svg"} with input as good
}

test_f0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "F0:")
}

test_f0_refuses_an_empty_measured_population if {
	some msg in p.deny with input as {"cases": [], "withheld": null}
	startswith(msg, "F0: no fonts")
	count(p.withheld) == 0 with input as {"cases": [], "withheld": null}
}

test_f0_withholds_without_fonttools if {
	w := {"cases": [], "withheld": "fontTools not installed (declared in pyproject; uv sync)"}
	count(p.deny) == 0 with input as w
	some msg in p.withheld with input as w
	startswith(msg, "F0: fontTools")
}

test_f1_refuses_a_missing_table if {
	some msg in p.deny with input as with_case(object.union(ttf("a.ttf"), {"tables_missing": ["OS/2"]}))
	msg == "F1: a.ttf: missing tables [\"OS/2\"]"
}

test_f2_refuses_a_cmap_gap if {
	some msg in p.deny with input as with_case(object.union(ttf("a.ttf"), {"cmap_missing": [" "]}))
	startswith(msg, "F2: a.ttf:")
}

# the selftest's dropped-contour build: every glyph one segment short
test_f3_refuses_a_dropped_segment if {
	some msg in p.deny with input as with_case(object.union(ttf("EL-Segment-7.ttf"), {"contour_mismatch": [{"glyph": "8", "contours": 6, "primitives": 7}]}))
	msg == "F3: EL-Segment-7.ttf: 8 has 6 contours, the substrate lights 7"
}

# the real SPEC-FLIP (session 23): an x-mirrored 2 / 7 / J / L / P
test_f4_refuses_a_spec_flip if {
	some msg in p.deny with input as with_case(object.union(ttf("EL-Segment-7.ttf"), {"flipped": ["2", "7", "J"]}))
	startswith(msg, "F4: EL-Segment-7.ttf: flipped")
}

test_f5_refuses_an_inked_space if {
	some msg in p.deny with input as with_case(object.union(ttf("a.ttf"), {"blank_inked": ["space"]}))
	startswith(msg, "F5:")
}

# the real closure off-by-one, both halves: baseline as the ROW index put every
# body glyph below the line; the first fix left no descender below it
test_f6_refuses_every_glyph_below_the_line if {
	bad := object.union(m58, {"below_baseline": ["A", "B", "g", "j", "p", "q", "y"]})
	some msg in p.deny with input as with_case(bad)
	msg == "F6: EL-Matrix-5x8.ttf: non-descenders below the baseline: [\"A\", \"B\"]"
}

test_f6_refuses_no_descender_below_the_line if {
	some msg in p.deny with input as with_case(object.union(m58, {"below_baseline": []}))
	startswith(msg, "F6: EL-Matrix-5x8.ttf: descenders not below the baseline")
}

test_f7_refuses_a_positive_descent if {
	some msg in p.deny with input as with_case(object.union(m58, {"descent": {"hhea": 0, "os2": -125}}))
	startswith(msg, "F7:")
}

test_f8_refuses_a_missing_svg_glyph if {
	some msg in p.deny with input as with_case(object.union(svg, {"missing": ["7"], "extra": ["x"]}))
	msg == "F8: EL-Segment-7.svg: missing [\"7\"] extra [\"x\"]"
}

test_f8_refuses_an_unparseable_svg if {
	some msg in p.deny with input as with_case(object.union(svg, {"parse_error": "no element found: line 1, column 0"}))
	startswith(msg, "F8: EL-Segment-7.svg: does not parse")
}
