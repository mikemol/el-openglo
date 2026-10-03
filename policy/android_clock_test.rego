package el.android_clock_test

import rego.v1

import data.el.android_clock

good := {"variant": "EL-Azure", "present": true, "parse_error": null, "missing_keys": [],
	"palette_mismatch": [], "geometry_mismatch": [], "digit_gaps": [], "current": true}

test_empty_population_denied if {
	count(android_clock.deny) == 1 with input as {}
}

test_complete_current_admitted if {
	inp := {"cases": [good], "orphans": [], "withheld": []}
	count(android_clock.deny) == 0 with input as inp
	count(android_clock.admitted) == 1 with input as inp
}

test_missing_file_denied if {
	some m in android_clock.deny with input as {"cases": [{"variant": "EL-Azure", "present": false}], "orphans": []}
	startswith(m, "D1: EL-Azure")
}

test_parse_error_denied if {
	inp := {"cases": [{"variant": "EL-Azure", "present": true, "parse_error": "bad"}], "orphans": []}
	some m in android_clock.deny with input as inp
	startswith(m, "D2: EL-Azure")
	count(android_clock.admitted) == 0 with input as inp
}

test_missing_section_denied if {
	some m in android_clock.deny with input as {"cases": [object.union(good, {"missing_keys": ["sources"]})], "orphans": []}
	startswith(m, "D3: EL-Azure: section sources")
}

test_blank_digit_denied if {
	some m in android_clock.deny with input as {"cases": [object.union(good, {"digit_gaps": ["8"]})], "orphans": []}
	startswith(m, "D3: EL-Azure: digit 8")
}

test_wrong_colour_denied if {
	inp := {"cases": [object.union(good, {"palette_mismatch": ["lit"]})], "orphans": []}
	some m in android_clock.deny with input as inp
	startswith(m, "D4: EL-Azure: palette.lit")
	count(android_clock.admitted) == 0 with input as inp
}

test_wrong_geometry_denied if {
	some m in android_clock.deny with input as {"cases": [object.union(good, {"geometry_mismatch": ["geometry.metrics"]})], "orphans": []}
	startswith(m, "D5: EL-Azure: geometry.metrics")
}

test_stale_denied if {
	some m in android_clock.deny with input as {"cases": [object.union(good, {"current": false})], "orphans": []}
	startswith(m, "D6: EL-Azure")
}

test_orphan_denied if {
	some m in android_clock.deny with input as {"cases": [good], "orphans": ["stray.json"]}
	startswith(m, "D7: orphan file stray.json")
}

test_withheld_only if {
	inp := {"cases": [], "orphans": [], "withheld": ["roster unreadable"]}
	count(android_clock.withheld) == 1 with input as inp
	count(android_clock.deny) == 0 with input as inp
}
