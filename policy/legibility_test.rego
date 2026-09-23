package el.legibility_test

import data.el.legibility as lg
import rego.v1

good := {"label": "latin-unifont-2to1", "font": "Unifont", "text": "Hello world 42", "lang": "eng", "rows": 8,
	"read": "Hello world 42", "score": 1.0}

test_admits_a_clean_read if {
	count(lg.deny) == 0 with input as {"cases": [good]}
	count(lg.withheld) == 0 with input as {"cases": [good]}
}

test_g0_refuses_no_cases if {
	some msg in lg.deny with input as {"cases": []}
	startswith(msg, "G0:")
}

test_g1_withholds_a_missing_reader if {
	some msg in lg.withheld with input as {"cases": [{"label": "cjk", "text": "世界", "lang": "chi_sim", "withheld": "tessdata for chi_sim is not installed"}]}
	startswith(msg, "G1:")
}

test_g2_refuses_a_read_below_the_floor if {
	# γ 1 at 2:1, as the sweep measured it: 'hii ad ees'
	some msg in lg.deny with input as {"cases": [object.union(good, {"read": "hii ad ees", "score": 0.143})]}
	startswith(msg, "G2:")
}

# a whole-number score (JSON 0 arrives as an int) must not print %!f(int=0)
test_g2_message_formats_a_whole_number if {
	some msg in lg.deny with input as {"cases": [object.union(good, {"read": "x", "score": 0})]}
	startswith(msg, "G2:")
	contains(msg, "score 0.000,")
	not contains(msg, "%!")
}

test_g3_refuses_an_empty_read if {
	some msg in lg.deny with input as {"cases": [object.union(good, {"read": "", "score": 0.0})]}
	startswith(msg, "G3:")
}
