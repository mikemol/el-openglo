package el.use_of_colour_test

import data.el.use_of_colour as uc
import rego.v1

critical_hue_only := {"id": "C6", "file": "templates/marquee-main.qml", "line": 464,
	"meaning": "critical urgency", "colour": [{"kind": "hue", "line": 464}], "cues": []}

low_opacity_only := {"id": "C7", "file": "templates/marquee-main.qml", "line": 466,
	"meaning": "low urgency", "colour": [{"kind": "opacity", "line": 466}], "cues": []}

critical_weighted := object.union(critical_hue_only, {"cues": [{"kind": "weight", "line": 468}]})

low_light := {"id": "C7", "file": "templates/marquee-main.qml", "line": 466,
	"meaning": "low urgency", "colour": [], "cues": [{"kind": "weight", "line": 468}]}

test_u0_refuses_an_absent_population if {
	some msg in uc.deny with input as {}
	startswith(msg, "U0:")
}

test_u0_refuses_an_empty_population if {
	some msg in uc.deny with input as {"cases": []}
	startswith(msg, "U0:")
}

test_u1_refuses_hue_alone if {
	some msg in uc.deny with input as {"cases": [critical_hue_only]}
	contains(msg, "C6")
	contains(msg, "(hue)")
}

test_u1_refuses_opacity_alone if {
	some msg in uc.deny with input as {"cases": [low_opacity_only]}
	contains(msg, "C7")
	contains(msg, "(opacity)")
}

test_u1_opacity_is_not_a_cue if {
	# opacity written as a cue is still colour: the ruling, not the measurement, decides
	disguised := object.union(low_opacity_only, {"cues": [{"kind": "opacity", "line": 466}]})
	some msg in uc.deny with input as {"cases": [disguised]}
	contains(msg, "C7")
}

test_admits_a_weight_cue if {
	inp := {"cases": [critical_weighted, low_light]}
	count(uc.deny) == 0 with input as inp
	uc.admitted == {"C6", "C7"} with input as inp
}

test_one_bad_case_denies_beside_good_ones if {
	inp := {"cases": [critical_weighted, low_opacity_only]}
	count(uc.deny) == 1 with input as inp
	uc.admitted == {"C6"} with input as inp
}

test_withheld_only_is_withheld_not_admitted if {
	inp := {"cases": [], "withheld": [{"id": "C15", "file": "make_schemes.py", "reason": "consumer-owned role"}]}
	count(uc.withheld) == 1 with input as inp
	count(uc.admitted) == 0 with input as inp
}
