package el.kerning_test

import data.el.kerning
import rego.v1

# a phase sweep: the widest interior stroke group over `frames` stepped frames
gap(style, group, frames) := {"variant": "V", "view": "gray", "style": style, "glyph_cols": 5, "frames": frames, "max_group": group}

# the admitting population: regular at the glyph width, bold one bloom column wider, swept over 15 frames
test_kerned_admits if {
	d := kerning.deny with input as {"gaps": [gap("regular", 5, 15), gap("bold", 6, 15)]}
	count(d) == 0
}

# K4: two letters fused at some scroll phase
test_fused_at_some_phase_denied if {
	d := kerning.deny with input as {"gaps": [gap("regular", 5, 15), gap("bold", 11, 15)]}
	some m in d
	startswith(m, "K4:")
}

# K4 is one column over the bloom: 7 where 6 is the limit
test_one_over_bloom_denied if {
	d := kerning.deny with input as {"gaps": [gap("regular", 5, 15), gap("bold", 7, 15)]}
	some m in d
	startswith(m, "K4:")
}

# K4 at the measured kern-loop mutation: a 30-column group denies
test_disabled_kern_loop_denied if {
	d := kerning.deny with input as {"gaps": [gap("regular", 5, 15), gap("bold", 30, 15)]}
	some m in d
	startswith(m, "K4:")
}

# K0: an absent population is a broken search
test_empty_population_denied if {
	d := kerning.deny with input as {}
	"K0: no view measured: the search is broken" in d
}

# K5: a regular-only sweep never tested the bloom
test_regular_only_denied if {
	d := kerning.deny with input as {"gaps": [gap("regular", 5, 15)]}
	"K5: no bold sweep measured" in d
}

# K6: a sweep of two frames met almost no phases
test_short_sweep_denied if {
	d := kerning.deny with input as {"gaps": [gap("regular", 5, 2), gap("bold", 6, 2)]}
	some m in d
	startswith(m, "K6:")
}

# the admitted set names what was judged, and a short sweep is not admitted
test_admitted_names_the_judged if {
	a := kerning.admitted with input as {"gaps": [gap("regular", 5, 15), gap("bold", 6, 2)]}
	a == {"V/regular/gray"}
}

test_withheld_is_not_denied if {
	i := {"gaps": [], "withheld": [{"variant": "V", "reason": "no qml"}]}
	d := kerning.deny with input as i
	w := kerning.withheld with input as i
	count(d) == 0
	count(w) == 1
}
