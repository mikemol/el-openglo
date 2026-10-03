package el.plasma_air_test

import data.el.plasma_air as p
import rego.v1

baker := {"id": "air", "has_colors_file": true, "colors_sections": ["Colors:View"], "svgs": [
	{"path": "widgets/button.svgz", "scheme_classed": 0, "baked": 256},
	{"path": "widgets/arrows.svgz", "scheme_classed": 14, "baked": 4},
]}

follower := {"id": "air", "has_colors_file": false, "colors_sections": [], "svgs": [
	{"path": "widgets/arrows.svgz", "scheme_classed": 14, "baked": 0},
]}

test_admits_recorded_bakes if {
	inp := {"themes": [baker]}
	count(p.deny) == 0 with input as inp
	p.verdicts == {"air": "bakes"} with input as inp
	p.admitted == {"air"} with input as inp
}

test_p1_refuses_a_stale_record if {
	inp := {"themes": [follower]}
	"P1: air is recorded as bakes but measures as follows" in p.deny with input as inp
	count(p.admitted) == 0 with input as inp
}

test_colors_file_alone_bakes if {
	t := object.union(follower, {"has_colors_file": true})
	p.verdicts == {"air": "bakes"} with input as {"themes": [t]}
}

test_unrecorded_theme_is_denied if {
	t := object.union(baker, {"id": "oxygen"})
	"P1: oxygen is recorded as unrecorded but measures as bakes" in p.deny with input as {"themes": [t]}
}

test_p0_refuses_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "P0:")
}

test_p0_refuses_empty_population if {
	some msg in p.deny with input as {"themes": []}
	startswith(msg, "P0:")
}

test_p2_refuses_empty_svgs if {
	t := object.union(baker, {"svgs": []})
	some msg in p.deny with input as {"themes": [t]}
	startswith(msg, "P2:")
}

test_withheld_only if {
	inp := {"themes": [{"id": "air", "withheld": "/x/air is not on this host"}]}
	count(p.deny) == 0 with input as inp
	count(p.withheld) == 1 with input as inp
	count(p.admitted) == 0 with input as inp
}
