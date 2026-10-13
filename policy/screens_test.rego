package el.screens_test

import data.el.screens as sc
import rego.v1

good := {"file": "clock-EL-Amber.png", "variant": "EL-Amber", "exists": true, "width": 400, "height": 48,
	"modal": "#1f170c", "distinct": 120, "grounds": ["#1f170c", "#140f08"]}

test_admits_clean if {
	count(sc.deny) == 0 with input as {"screens": [good]}
}

scroll := {"file": "marquee-anim-EL-Amber.png", "variant": "EL-Amber", "exists": true, "frames": 61,
	"tears": [], "seamless": true, "shifts": [2.75, 3.0, 2.5, 2.75, 3.25, 2.5]}

s8(inp) := [m | some m in sc.deny with input as inp; startswith(m, "S8")]

s8_withheld(inp) := [m | some m in sc.withheld with input as inp; startswith(m, "S8")]

with_steps(steps) := {"screens": [good], "animations": [object.union(scroll, {"logged_steps": steps})]}

# W60 / W201 / S8: move the content, then sample. At least 2/3 of the MOVING steps are fractional.
test_s8_admits_a_scroll_that_moves_by_fractions_of_a_pip if {
	count(s8({"screens": [good], "animations": [scroll]})) == 0
}

# the old rule denied only when EVERY step was whole; one fractional step carried a pixelated run
test_s8_refuses_a_scroll_that_moves_only_by_whole_pips if {
	inp := {"screens": [good], "animations": [object.union(scroll, {"shifts": [3.0, 3.0, 2.0, 3.0]})]}
	"S8: marquee-anim-EL-Amber.png: only 0 of 4 moving step(s) are fractional, under 2/3 — pixelated, then moved" in sc.deny with input as inp
}

test_s8_one_fractional_step_among_whole_ones_is_refused if {
	inp := {"screens": [good], "animations": [object.union(scroll, {"shifts": [3.0, 3.0, 2.75, 3.0, 2.0]})]}
	count(s8(inp)) == 1
}

test_s8_a_negative_fractional_shift_counts if {
	inp := {"screens": [good], "animations": [object.union(scroll, {"shifts": [-1.25, 0.0, 2.75]})]}
	count(s8(inp)) == 0
}

# the boundary is 2/3, inclusive
test_s8_exactly_two_thirds_fractional_is_admitted if {
	count(s8(with_steps([2.5, 2.5, 3.0]))) == 0
}

test_s8_just_under_two_thirds_is_refused if {
	"S8: marquee-anim-EL-Amber.png: only 1 of 3 moving step(s) are fractional, under 2/3 — pixelated, then moved" in sc.deny with input as with_steps([2.5, 3.0, 3.0])
}

# W208: the harness's logged offsets decide where they exist, in BOTH directions
test_s8_logged_fractional_steps_admit_even_when_the_image_fit_reads_whole if {
	inp := {"screens": [good], "animations": [object.union(scroll, {"shifts": [3.0, 3.0, 3.0, 3.0], "logged_steps": [4.618, 4.618, 4.618]})]}
	count(s8(inp)) == 0
}

test_s8_logged_whole_steps_refuse_even_when_the_image_fit_reads_fractional if {
	inp := {"screens": [good], "animations": [object.union(scroll, {"logged_steps": [3.0, 3.0, 3.0]})]}
	count(s8(inp)) == 1
}

# whole is within 0.001 of an integer: float noise on a whole step is not a fraction
test_s8_float_noise_on_a_whole_step_is_still_whole if {
	count(s8(with_steps([3.0000000000000004, 3.0, 3.0]))) == 1
}

# a stall is not a move: zero steps are excluded from the share
test_s8_zero_steps_are_excluded if {
	count(s8(with_steps([0.0, 0.0, 4.5, 4.75, 0.0]))) == 0
	count(s8_withheld(with_steps([0.0, 0.0, 4.5, 4.75, 0.0]))) == 0
}

# withheld, never judged and never admitted: nothing measured, or only stalls
test_s8_a_run_with_no_step_at_all_is_withheld if {
	inp := {"screens": [good], "animations": [object.union(scroll, {"shifts": []})]}
	count(s8(inp)) == 0
	s8_withheld(inp) == ["S8: marquee-anim-EL-Amber.png: no step was measured (no logged offsets, no image-fit shift)"]
	count(sc.admitted) == 1 with input as inp
}

test_s8_an_all_stall_run_is_withheld_and_not_admitted if {
	inp := with_steps([0.0, 0.0, 0.0])
	count(s8(inp)) == 0
	s8_withheld(inp) == ["S8: marquee-anim-EL-Amber.png: every step is a stall, so there is nothing to judge"]
	sc.admitted == {"clock-EL-Amber.png"} with input as inp
}

test_s8_a_judged_scroll_is_admitted if {
	sc.admitted == {"clock-EL-Amber.png", "marquee-anim-EL-Amber.png"} with input as {"screens": [good], "animations": [scroll]}
}

# W209 / S5 (logged): the harness's own offsets decide where they exist
s5(inp) := [m | some m in sc.deny with input as inp; startswith(m, "S5")]

test_s5_logged_uniform_steps_admit_even_when_the_image_fit_reports_tears if {
	inp := {"screens": [good], "animations": [object.union(scroll, {
		"tears": [{"frame": 18, "shift": 2.75, "mismatch": 9.1, "total": 12.0}],
		"logged_steps": [2.75, 2.75, 2.75, 2.75],
	})]}
	count(s5(inp)) == 0
}

test_s5_logged_off_step_denies_and_names_the_frame if {
	inp := {"screens": [good], "animations": [object.union(scroll, {"logged_steps": [2.75, 2.75, -40.0, 2.75]})]}
	"S5: marquee-anim-EL-Amber.png tears at frame(s) [4] - logged step off the run's 2.75 pip" in sc.deny with input as inp
}

test_s5_without_a_log_the_image_fit_still_judges if {
	inp := {"screens": [good], "animations": [object.union(scroll, {
		"tears": [{"frame": 7, "shift": 2.75, "mismatch": 9.1, "total": 12.0}],
		"logged_steps": null,
	})]}
	"S5: marquee-anim-EL-Amber.png tears at frame(s) [7]" in sc.deny with input as inp
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
	"shifts": [2.75, 3.0, 2.5, 2.75, 3.25, 3.0], "tears": [], "seamless": true}

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
