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

# ── the floor band: every score lands in EXACTLY ONE of deny / withheld / admitted ──

# the verdict classes a single case lands in
classes(c) := out if {
	d := lg.deny with input as {"cases": [c]}
	w := lg.withheld with input as {"cases": [c]}
	a := lg.admitted with input as {"cases": [c]}
	out := {k | some k, s in {"deny": d, "withheld": w, "admitted": a}; count(s) > 0}
}

at(score) := object.union(good, {"read": "Hello wor1d 42", "score": score})

test_floor_054_denied_only if {
	classes(at(0.54)) == {"deny"}
	some msg in lg.deny with input as {"cases": [at(0.54)]}
	startswith(msg, "G2:")
}

test_floor_055_admitted_only if {
	classes(at(0.55)) == {"admitted"}
}

# 0.6 and 0.69 were the unjudged band: below admitted's old 0.7, above G2's 0.55
test_floor_060_admitted_only if {
	classes(at(0.6)) == {"admitted"}
}

test_floor_069_admitted_only if {
	classes(at(0.69)) == {"admitted"}
}

test_floor_070_admitted_only if {
	classes(at(0.7)) == {"admitted"}
}

# the CURRENT honest reads (s134) are admitted, not silently unjudged
test_current_honest_reads_admitted if {
	"latin-liberation" in lg.admitted with input as {"cases": [object.union(at(0.562), {"label": "latin-liberation"})]}
	"latin-unifont-1to1" in lg.admitted with input as {"cases": [object.union(at(0.643), {"label": "latin-unifont-1to1"})]}
}

test_g4_non_latin_read_withheld_only if {
	cjk := {"label": "cjk-unifont-1to1", "text": "世界", "lang": "chi_sim", "read": "世界", "score": 1.0}
	classes(cjk) == {"withheld"}
	some msg in lg.withheld with input as {"cases": [cjk]}
	startswith(msg, "G4:")
}

test_g4_unscored_latin_read_withheld_only if {
	classes(object.union(good, {"score": null})) == {"withheld"}
}

# a null withheld is NOT a withholding: the case is judged like any measured one
test_null_withheld_is_judged if {
	classes(object.union(good, {"withheld": null})) == {"admitted"}
	classes(object.union(at(0.3), {"withheld": null})) == {"deny"}
}
