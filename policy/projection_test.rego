package el.projection_test

import data.el.projection as p
import rego.v1

g(ch, proj) := {"ch": ch, "authored": ["a", "b"], "projected": proj, "jaccard": 0.5}

good := {"font": "/usr/share/fonts/LiberationMono-Regular.ttf", "fmt": "16", "frame": "stretch",
	"glyphs": [g("A", ["a", "b"]), g("B", ["c"]), g("C", ["d", "e"]), g("D", ["f"])]}

test_admits_a_discriminating_projection if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	p.admitted == {"projection"} with input as good
}

# agreement is reported, not gated: every glyph disagreeing still admits
test_low_agreement_is_not_denied if {
	low := object.union(good, {"glyphs": [object.union(x, {"jaccard": 0}) | some x in good.glyphs]})
	count(p.deny) == 0 with input as low
}

# the old silent pass: no TTF printed SKIP and exited 0
test_v0_withholds_without_a_font if {
	inp := {"font": null, "fmt": "16", "frame": "stretch", "glyphs": []}
	"V0: no TTF was found on this host; 0 authored glyphs projected" in p.withheld with input as inp
	count(p.admitted) == 0 with input as inp
	count(p.deny) == 0 with input as inp
}

test_v0_withholds_an_absent_measurement if {
	"V0: font was not measured" in p.withheld with input as {}
	count(p.admitted) == 0 with input as {}
}

test_v0_refuses_an_empty_projection if {
	"V0: a font was found but the authored table projected to nothing; nothing was validated" in p.deny with input as object.union(good, {"glyphs": []})
}

# the one gated fact: a matcher that sees no ink projects every glyph alike
test_v1_refuses_a_blind_matcher if {
	blind := object.union(good, {"glyphs": [g("A", ["x"]), g("B", ["x"]), g("C", ["x"]), g("D", ["x"])]})
	"V1: only 1 distinct projection(s) over 4 glyphs; the matcher is not seeing the ink" in p.deny with input as blind
	count(p.admitted) == 0 with input as blind
}

test_all_null_glyph_withheld_only if {
	inp := object.union(good, {"glyphs": [{"ch": "A", "authored": null, "projected": null, "jaccard": null}]})
	"W: glyph A: projected was not measured" in p.withheld with input as inp
	count(p.admitted) == 0 with input as inp
}
