package el.screens_test

import data.el.screens as sc
import rego.v1

good := {"file": "clock-EL-Amber.png", "variant": "EL-Amber", "exists": true, "width": 400, "height": 48,
	"modal": "#1f170c", "distinct": 120, "grounds": ["#1f170c", "#140f08"]}

test_admits_clean if {
	count(sc.deny) == 0 with input as {"screens": [good]}
}

scroll := {"file": "marquee-anim-EL-Amber.png", "variant": "EL-Amber", "exists": true, "frames": 61,
	"tears": [], "seamless": true, "shifts": [2.75, 3.0, 2.5, 3.0]}

# W60 / S8: move the content, then sample — a fractional shift is the evidence
test_s8_admits_a_scroll_that_moves_by_fractions_of_a_pip if {
	count([m | some m in sc.deny; startswith(m, "S8")]) == 0 with input as {"screens": [good], "animations": [scroll]}
}

test_s8_refuses_a_scroll_that_moves_only_by_whole_pips if {
	inp := {"screens": [good], "animations": [object.union(scroll, {"shifts": [3.0, 3.0, 2.0, 3.0]})]}
	"S8: marquee-anim-EL-Amber.png moves only by whole pips over 4 frame pair(s) — pixelated, then moved" in sc.deny with input as inp
}

test_s8_a_negative_fractional_shift_counts if {
	inp := {"screens": [good], "animations": [object.union(scroll, {"shifts": [-1.25, 0.0, 2.0]})]}
	count([m | some m in sc.deny; startswith(m, "S8")]) == 0 with input as inp
}

test_s8_does_not_judge_a_run_with_no_measured_shift if {
	inp := {"screens": [good], "animations": [object.union(scroll, {"shifts": []})]}
	count([m | some m in sc.deny; startswith(m, "S8")]) == 0 with input as inp
}

test_s0_refuses_no_plan if {
	some msg in sc.deny with input as {"screens": []}
	startswith(msg, "S0:")
}

test_s1_refuses_a_missing_still if {
	some msg in sc.deny with input as {"screens": [{"file": "switcher-EL-Amber.png", "variant": "EL-Amber", "exists": false, "grounds": ["#1f170c", "#140f08"]}]}
	startswith(msg, "S1:")
}

test_s2_refuses_a_blank_still if {
	some msg in sc.deny with input as {"screens": [object.union(good, {"distinct": 1})]}
	startswith(msg, "S2:")
}

test_s3_refuses_the_wrong_ground if {
	some msg in sc.deny with input as {"screens": [object.union(good, {"modal": "#081411"})]}
	startswith(msg, "S3:")
}

test_s3_admits_the_view_ground if {
	count(sc.deny) == 0 with input as {"screens": [object.union(good, {"modal": "#140f08"})]}
}

# shifts in PIPS with quarter-pip fractions, as render_screens.animation_facts measures
# since W54 (this fixture was [6, 6, 7, 6, 12, 6], whole-pixel steps from before the
# aperture field — under today's unit exactly the pixelate-then-move shape S8 refuses)
anim := {"file": "marquee-anim-EL-Amber.png", "variant": "EL-Amber", "exists": true, "frames": 48, "width": 420,
	"shifts": [2.75, 3.0, 2.5, 3.0, 2.75, 3.0], "tears": [], "seamless": true}

test_s6_refuses_an_open_loop if {
	some msg in sc.deny with input as {"screens": [good], "animations": [object.union(anim, {"seamless": false})]}
	startswith(msg, "S6:")
}

test_s4_s5_admit_a_scrolling_animation if {
	count(sc.deny) == 0 with input as {"screens": [good], "animations": [anim]}
}

test_s4_refuses_a_missing_animation if {
	some msg in sc.deny with input as {"screens": [good], "animations": [{"file": "marquee-anim-EL-Amber.png", "variant": "EL-Amber", "exists": false}]}
	startswith(msg, "S4:")
}

test_s4_refuses_a_still_with_a_loop_flag if {
	some msg in sc.deny with input as {"screens": [good], "animations": [object.union(anim, {"frames": 1})]}
	startswith(msg, "S4:")
}

test_s5_refuses_a_tear if {
	some msg in sc.deny with input as {"screens": [good], "animations": [object.union(anim, {"tears": [{"frame": 3, "shift": 0, "mismatch": 40, "lit": 90}]})]}
	startswith(msg, "S5:")
}

# N1 fix (S1 `not s.exists`): a null existence was not measured — withheld, never "missing"
test_null_screen_exists_withheld_not_s1 if {
	inp := {"screens": [object.union(good, {"exists": null})], "animations": []}
	count(sc.deny) == 0 with input as inp
	sc.withheld == {"S7: clock-EL-Amber.png: exists was not measured"} with input as inp
	count(sc.admitted) == 0 with input as inp
}

# N1 fix (S4 `not a.exists`)
test_null_animation_exists_withheld_not_s4 if {
	inp := {"screens": [good], "animations": [object.union(anim, {"exists": null})]}
	count(sc.deny) == 0 with input as inp
	sc.withheld == {"S7: marquee-anim-EL-Amber.png: exists was not measured"} with input as inp
	sc.admitted == {"clock-EL-Amber.png"} with input as inp
}

# N1 fix (S6 `not a.seamless`)
test_null_seamless_withheld_not_s6 if {
	inp := {"screens": [good], "animations": [object.union(anim, {"seamless": null})]}
	count(sc.deny) == 0 with input as inp
	sc.withheld == {"S7: marquee-anim-EL-Amber.png: seamless was not measured"} with input as inp
}

test_all_null_case_withheld_only if {
	s := {"file": "clock-EL-Amber.png", "variant": "EL-Amber", "exists": true, "modal": null, "distinct": null, "grounds": null}
	a := {"file": "marquee-anim-EL-Amber.png", "variant": "EL-Amber", "exists": true, "frames": null, "tears": null, "seamless": null}
	inp := {"screens": [s], "animations": [a]}
	count(sc.deny) == 0 with input as inp
	count(sc.admitted) == 0 with input as inp
	w := sc.withheld with input as inp
	count(w) == 6
	"S7: clock-EL-Amber.png: distinct was not measured" in w
	"S7: marquee-anim-EL-Amber.png: seamless was not measured" in w
}

test_null_animations_population_withheld if {
	inp := {"screens": [good], "animations": null}
	sc.withheld == {"S7: animations was not measured"} with input as inp
	count(sc.deny) == 0 with input as inp
}

test_admits_a_clean_still_and_animation if {
	sc.admitted == {"clock-EL-Amber.png", "marquee-anim-EL-Amber.png"} with input as {"screens": [good], "animations": [anim]}
}

test_a_denied_still_is_not_admitted if {
	count(sc.admitted) == 0 with input as {"screens": [object.union(good, {"distinct": 1})], "animations": []}
}

# null exists is not held: the drawn-content rules S2/S3 judge only an existing still
test_null_screen_exists_does_not_fire if {
	inp := {"screens": [object.union(good, {"exists": null, "distinct": 1, "modal": "#081411"})]}
	d := sc.deny with input as inp
	every msg in d {
		not startswith(msg, "S2:")
		not startswith(msg, "S3:")
	}
}

# null exists is not held: the frame rules S4(frames)/S5/S6 judge only an existing animation
test_null_animation_exists_does_not_fire if {
	bad := object.union(anim, {"exists": null, "frames": 1, "seamless": false,
		"tears": [{"frame": 3, "shift": 0, "mismatch": 40, "lit": 90}]})
	inp := {"screens": [good], "animations": [bad]}
	d := sc.deny with input as inp
	every msg in d {
		not contains(msg, "frame(s) — not an animation")
		not startswith(msg, "S5:")
		not startswith(msg, "S6:")
	}
}
