package el.urgency_cues_test

import data.el.urgency_cues
import rego.v1

facts(ul) := {"gray": {"mass": 0.8, "footprint": 0.7, "underline": ul}, "tritanomaly": {"mass": 0.8, "footprint": 0.7, "underline": ul}}

steady := {"frames": 90, "covered": 60, "dark": 0, "edges": 0, "span_ms": 0, "hz": 0, "steady_min": 0.82}

flashing(hz) := {"frames": 90, "covered": 60, "dark": 30, "edges": 10, "span_ms": 2250, "hz": hz, "steady_min": 0.9}

# the shape of a measured variant: lowercase low, upper-case normal, flashing
# underlined critical (numbers of the order the real board gives)
case(lo_norm, norm_crit, crit_t) := {
	"variant": "EL-Fixture",
	"urgencies": {"critical": facts(1.0)},
	"pairs": [
		{"a": "low", "b": "normal", "shape": lo_norm, "view": "tritanomaly", "mass_ratio": 1.0},
		{"a": "low", "b": "critical", "shape": 0.55, "view": "gray", "mass_ratio": 1.1},
		{"a": "normal", "b": "critical", "shape": norm_crit, "view": "gray", "mass_ratio": 1.1},
	],
	"temporal": {"low": steady, "normal": steady, "critical": crit_t},
	"pause": {"paused_samples": 20, "paused_dark": 0, "paused_ms": 760, "running_dark": 4},
}

letter(ch, u, shown, key, partner) := {"ch": ch, "forms": [{"urgency": u, "shown": shown, "key": key, "partner_in_charset": partner, "case_applied": key == shown}]}

charset := {"flash_hz": 2, "flash_ms": 500, "cases":[letter("A", 0, "a", "a", true), letter("a", 1, "A", "A", true)]}

good := {"cases": [case(0.42, 0.24, flashing(2.0))], "withheld": [], "charset": charset}

# object.union MERGES nested objects; replacing one wholesale needs the key removed first
with_key(o, k, v) := object.union(object.remove(o, [k]), {k: v})

denials(inp, prefix) :={m | some m in urgency_cues.deny with input as inp; startswith(m, prefix)}

# admitting: letterform low, flashing underlined critical
test_letterform_admitted if {
	count(urgency_cues.deny) == 0 with input as good
	urgency_cues.admitted == {"EL-Fixture"} with input as good
}

# the boundary is the floor, inclusive
test_exactly_at_shape_min_admitted if {
	count(urgency_cues.deny) == 0 with input as object.union(good, {"cases": [case(0.15, 0.24, flashing(2.0))]})
}

# refusing: an OPACITY-ONLY low — the measured first run (the -s/4 light dot, the same
# pips at ~1/4 brightness): its lit-pip set is normal's, shape 0
test_opacity_only_low_denied if {
	d := denials(object.union(good, {"cases": [case(0.0, 0.24, flashing(2.0))]}), "V1: EL-Fixture: low and normal")
	count(d) == 1
}

# refusing: a COLOUR-ONLY critical — hot ink, same letters, no underline, no flash
test_colour_only_critical_denied if {
	c := object.union(case(0.42, 0.0, steady), {"urgencies": {"critical": facts(0.0)}})
	inp := object.union(good, {"cases": [c]})
	count(denials(inp, "V1: EL-Fixture: normal and critical")) == 1
	count(denials(inp, "V3:")) == 2
	count(denials(inp, "V5:")) == 1
}

# refusing: a flash FASTER than WCAG 2.3.1's three per second
test_flash_over_3hz_denied if {
	inp := object.union(good, {"cases": [case(0.42, 0.24, flashing(4.0))]})
	count(denials(inp, "V6: EL-Fixture: critical flashes at 4.00 Hz")) == 1
}

# ...and one at 2.8 Hz is under WCAG but off the declared 2 Hz
test_flash_off_declared_rate_denied if {
	inp := object.union(good, {"cases": [case(0.42, 0.24, flashing(2.8))]})
	count(denials(inp, "V7: EL-Fixture:")) == 1
	count(denials(inp, "V6:")) == 0
}

test_declared_rate_over_operator_ceiling_denied if {
	inp := object.union(good, {"charset": object.union(charset, {"flash_hz": 2.5}), "cases": [case(0.42, 0.24, flashing(2.5))]})
	count(denials(inp, "V7: the declared flash rate 2.50 Hz")) == 1
}

test_no_declared_rate_denied if {
	inp := with_key(good, "charset", {"cases": charset.cases})
	"V7: no declared flash rate measured (Body.FLASH_HZ)" in urgency_cues.deny with input as inp
}

# refusing: a steady urgency that flashes, and one that dips
test_flashing_low_denied if {
	c := object.union(case(0.42, 0.24, flashing(2.0)), {"temporal": {"low": flashing(2.0), "normal": steady, "critical": flashing(2.0)}})
	count(denials(object.union(good, {"cases": [c]}), "V8: EL-Fixture: low flashes")) == 1
}

test_dipping_normal_denied if {
	c := object.union(case(0.42, 0.24, flashing(2.0)), {"temporal": {"low": steady, "normal": object.union(steady, {"steady_min": 0.3}), "critical": flashing(2.0)}})
	count(denials(object.union(good, {"cases": [c]}), "V8: EL-Fixture: normal's lit mass")) == 1
}

test_too_few_covered_frames_denied if {
	c := object.union(case(0.42, 0.24, flashing(2.0)), {"temporal": {"low": steady, "normal": steady, "critical": object.union(flashing(2.0), {"covered": 3})}})
	count(denials(object.union(good, {"cases": [c]}), "V4: EL-Fixture: critical")) == 1
}

# refusing: a flash the hover-pause does not stop (WCAG 2.2.2), or a pause never seen
test_unpausable_flash_denied if {
	c := object.union(case(0.42, 0.24, flashing(2.0)), {"pause": {"paused_samples": 20, "paused_dark": 9, "running_dark": 4}})
	count(denials(object.union(good, {"cases": [c]}), "V9: EL-Fixture: 9 of 20")) == 1
}

test_short_pause_denied if {
	c := object.union(case(0.42, 0.24, flashing(2.0)), {"pause": {"paused_samples": 3, "paused_ms": 80}})
	count(denials(object.union(good, {"cases": [c]}), "V9: EL-Fixture: the hover-pause held 80 ms")) == 1
}

test_unmeasured_pause_denied if {
	c := with_key(case(0.42, 0.24, flashing(2.0)), "pause", {})
	count(denials(object.union(good, {"cases": [c]}), "V9: EL-Fixture: the hover-pause never held")) == 1
}

# refusing: a lowercase glyph the registry lacks (the case cue lost), and a '?'
test_missing_lowercase_denied if {
	cs := object.union(charset, {"cases": [letter("Q", 0, "q", "Q", true)]})
	count(denials(object.union(good, {"charset": cs}), "V10: \"Q\" at urgency 0")) == 1
}

test_question_mark_denied if {
	cs := object.union(charset, {"cases": [letter("q", 0, "q", "?", true)]})
	count(denials(object.union(good, {"charset": cs}), "V10:")) == 2
}

# admitting: a partner OUTSIDE the charset (ÿ -> Ÿ is not Latin-1) falls back to the sent char
test_partner_outside_charset_admitted if {
	cs := object.union(charset, {"cases": [letter("ÿ", 1, "Ÿ", "ÿ", false)]})
	count(denials(object.union(good, {"charset": cs}), "V10:")) == 0
}

test_empty_charset_denied if {
	"V10: the charset census measured no letters" in urgency_cues.deny with input as with_key(good, "charset", {"flash_hz": 2})
}

test_missing_pair_denied if {
	c := object.union(case(0.42, 0.24, flashing(2.0)), {"pairs": [{"a": "low", "b": "normal", "shape": 0.4, "view": "gray", "mass_ratio": 1.1}]})
	count(denials(object.union(good, {"cases": [c]}), "V2:")) == 1
}

test_null_shape_denied if {
	c := object.union(case(0.42, 0.24, flashing(2.0)), {"pairs": [
		{"a": "low", "b": "normal", "shape": null, "view": "gray"},
		{"a": "low", "b": "critical", "shape": 0.5, "view": "gray"},
		{"a": "normal", "b": "critical", "shape": 0.3, "view": "gray"},
	]})
	count(denials(object.union(good, {"cases": [c]}), "V1: EL-Fixture: low~normal has no shape")) == 1
}

test_unlit_underline_denied if {
	c := object.union(case(0.42, 0.24, flashing(2.0)), {"urgencies": {"critical": facts(0.1)}})
	count(denials(object.union(good, {"cases": [c]}), "V3:")) == 2
}

test_null_underline_denied if {
	c := object.union(case(0.42, 0.24, flashing(2.0)), {"urgencies": {"critical": {"gray": {"underline": null}}}})
	count(denials(object.union(good, {"cases": [c]}), "V3:")) == 1
}

test_empty_population_denied if {
	"V0: no variant measured: the search is broken" in urgency_cues.deny with input as {"cases": [], "withheld": []}
}

test_absent_population_denied if {
	"V0: no variant measured: the search is broken" in urgency_cues.deny with input as {}
}

# a runner-less host is withheld, not denied and not admitted
test_runnerless_is_withheld_only if {
	inp := {"cases": [], "withheld": [{"variant": "*", "reason": "no qml runner on this host"}], "charset": null}
	count(urgency_cues.deny) == 0 with input as inp
	count(urgency_cues.withheld) == 1 with input as inp
}
