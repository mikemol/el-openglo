package el.kerning_test

import data.el.kerning
import rego.v1

case(style, runs) := {"variant": "V", "view": "gray", "style": style, "glyph_cols": 5, "interior_runs": runs}

# the admitting case: regular at the glyph width, bold one bloom column wider
test_kerned_admits if {
	d := kerning.deny with input as {"cases": [case("regular", [5, 5, 2, 5]), case("bold", [6, 6, 2, 6])]}
	count(d) == 0
}

# the refusing cases
test_merged_pair_denied if {
	d := kerning.deny with input as {"cases": [case("regular", [5, 5]), case("bold", [6, 12, 6])]}
	some m in d
	startswith(m, "K1:")
}

test_one_over_bloom_denied if {
	d := kerning.deny with input as {"cases": [case("regular", [5]), case("bold", [7])]}
	some m in d
	startswith(m, "K1:")
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
