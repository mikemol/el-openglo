package el.screens_test

import data.el.screens as sc
import rego.v1

good := {"file": "clock-EL-Amber.png", "variant": "EL-Amber", "exists": true, "width": 400, "height": 48,
	"modal": "#1f170c", "distinct": 120, "grounds": ["#1f170c", "#140f08"]}

test_admits_clean if {
	count(sc.deny) == 0 with input as {"screens": [good]}
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

anim := {"file": "marquee-anim-EL-Amber.png", "variant": "EL-Amber", "exists": true, "frames": 48, "width": 420,
	"shifts": [6, 6, 7, 6, 12, 6], "tears": [], "seamless": true}

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
