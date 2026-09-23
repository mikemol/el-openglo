package el.urgency_cues_test

import data.el.urgency_cues
import rego.v1

facts(ul) := {"gray": {"mass": 0.8, "footprint": 0.7, "underline": ul}, "tritanomaly": {"mass": 0.8, "footprint": 0.7, "underline": ul}}

case(lo_norm) := {
	"variant": "EL-Fixture",
	"urgencies": {"critical": facts(1.0)},
	"pairs": [
		{"a": "low", "b": "normal", "ratio": lo_norm, "view": "tritanomaly", "mass_ratio": 3.9},
		{"a": "low", "b": "critical", "ratio": 2.4, "view": "gray", "mass_ratio": 4.9},
		{"a": "normal", "b": "critical", "ratio": 2.3, "view": "gray", "mass_ratio": 1.4},
	],
}

# refusing: the measured first run — a light dot that is only dimmer (ratio ~1.03)
test_opacity_only_light_dot_denied if {
	d := urgency_cues.deny with input as {"cases": [case(1.031)], "withheld": [], "threshold": 1.25}
	some m in d
	startswith(m, "V1: EL-Fixture: low and normal")
}

# admitting: the whole-pip light glyph (ratio ~1.9)
test_weight_step_admitted if {
	count(urgency_cues.deny) == 0 with input as {"cases": [case(1.87)], "withheld": [], "threshold": 1.25}
	urgency_cues.admitted == {"EL-Fixture"} with input as {"cases": [case(1.87)], "withheld": [], "threshold": 1.25}
}

# the boundary is the floor, inclusive
test_exactly_at_threshold_admitted if {
	count(urgency_cues.deny) == 0 with input as {"cases": [case(1.25)], "withheld": [], "threshold": 1.25}
}

test_empty_population_denied if {
	"V0: no variant measured: the search is broken" in urgency_cues.deny with input as {"cases": [], "withheld": []}
}

test_absent_population_denied if {
	"V0: no variant measured: the search is broken" in urgency_cues.deny with input as {}
}

# a runner-less host is withheld, not denied and not admitted
test_runnerless_is_withheld_only if {
	inp := {"cases": [], "withheld": [{"variant": "*", "reason": "no qml runner on this host"}]}
	count(urgency_cues.deny) == 0 with input as inp
	count(urgency_cues.withheld) == 1 with input as inp
}

test_missing_pair_denied if {
	c := object.union(case(1.9), {"pairs": [{"a": "low", "b": "normal", "ratio": 1.9, "view": "gray", "mass_ratio": 1.1}]})
	some m in urgency_cues.deny with input as {"cases": [c], "threshold": 1.25}
	startswith(m, "V2:")
}

test_unlit_underline_denied if {
	c := object.union(case(1.9), {"urgencies": {"critical": facts(0.1)}})
	some m in urgency_cues.deny with input as {"cases": [c], "threshold": 1.25}
	startswith(m, "V3:")
}
