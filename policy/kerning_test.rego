package el.kerning_test

import data.el.kerning
import rego.v1

case(style, runs) := {"variant": "V", "view": "gray", "style": style, "glyph_cols": 5, "interior_runs": runs}

# a phase sweep: the widest interior stroke group over `frames` stepped frames
gap(style, group, frames) := {"variant": "V", "view": "gray", "style": style, "glyph_cols": 5, "frames": frames, "max_group": group}

sweep := [gap("regular", 5, 15), gap("bold", 6, 15)]

# the admitting case: regular at the glyph width, bold one bloom column wider, and the sweep agrees
test_kerned_admits if {
	d := kerning.deny with input as {"cases": [case("regular", [5, 5, 2, 5]), case("bold", [6, 6, 2, 6])], "gaps": sweep}
	count(d) == 0
}

# the refusing cases
test_merged_pair_denied if {
	d := kerning.deny with input as {"cases": [case("regular", [5, 5]), case("bold", [6, 12, 6])], "gaps": sweep}
	some m in d
	startswith(m, "K1:")
}

test_one_over_bloom_denied if {
	d := kerning.deny with input as {"cases": [case("regular", [5]), case("bold", [7])], "gaps": sweep}
	some m in d
	startswith(m, "K1:")
}

# K4: the one-moment still is clean but a phase of the sweep fuses two letters
test_fused_at_some_phase_denied if {
	d := kerning.deny with input as {
		"cases": [case("regular", [5, 5]), case("bold", [6, 6])],
		"gaps": [gap("regular", 5, 15), gap("bold", 11, 15)],
	}
	some m in d
	startswith(m, "K4:")
}

# K4 admits the measured widths: bold one bloom wider at every phase
test_bold_bloom_at_every_phase_admits if {
	d := kerning.deny with input as {
		"cases": [case("regular", [5, 5]), case("bold", [6, 6])],
		"gaps": [gap("regular", 5, 15), gap("bold", 6, 15)],
	}
	count(d) == 0
}

# K5: cases with no sweep judged one phase only
test_no_sweep_denied if {
	d := kerning.deny with input as {"cases": [case("regular", [5, 5]), case("bold", [6, 6])]}
	some m in d
	startswith(m, "K5:")
}

# K6: a sweep of two frames met almost no phases
test_short_sweep_denied if {
	d := kerning.deny with input as {
		"cases": [case("regular", [5, 5]), case("bold", [6, 6])],
		"gaps": [gap("regular", 5, 2), gap("bold", 6, 2)],
	}
	some m in d
	startswith(m, "K6:")
}

test_empty_population_denied if {
	d := kerning.deny with input as {}
	"K0: no view measured: the search is broken" in d
}

test_nothing_to_judge_denied if {
	d := kerning.deny with input as {"cases": [case("regular", []), case("bold", [6])]}
	some m in d
	startswith(m, "K2:")
}

test_regular_only_denied if {
	d := kerning.deny with input as {"cases": [case("regular", [5, 5])]}
	"K3: no bold view measured" in d
}

test_withheld_is_not_denied if {
	i := {"cases": [], "withheld": [{"variant": "V", "reason": "no qml"}]}
	d := kerning.deny with input as i
	w := kerning.withheld with input as i
	count(d) == 0
	count(w) == 1
}
