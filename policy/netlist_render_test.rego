package el.netlist_render_test

import data.el.netlist_render as p
import rego.v1

good := {
	"frames": 3, "stuck": [],
	"render": {"ok": true, "detail": ""},
	"families": [{"family": "geometry", "colour": "#4080ff", "in_dot": true, "in_svg": true}],
	"cases": [{"node": "view", "in_dot": true}, {"node": "fg", "in_dot": true}],
}

test_admits_a_rendered_graph if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	count(p.admitted) == 2 with input as good
}

test_n0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "N0:")
}

# the old selftest: NR.frames stubbed to [] — "an empty sequence is seen"
test_n0_refuses_an_empty_sequence if {
	some msg in p.deny with input as object.union(good, {"frames": 0})
	msg == "N0: no elimination frames; the solve did not run"
}

test_n2_refuses_a_node_missing_from_the_render if {
	some msg in p.deny with input as object.union(good, {"cases": [{"node": "view", "in_dot": true}, {"node": "fg", "in_dot": false}]})
	msg == "N2: node \"fg\" is in the graph and not in the render"
}

# the `edgecolor=` defect the docstring names: the dot loads, the colour is gone
test_n3_refuses_a_colour_lost_in_the_svg if {
	bad := object.union(good, {"families": [{"family": "geometry", "colour": "#4080ff", "in_dot": true, "in_svg": false}]})
	some msg in p.deny with input as bad
	startswith(msg, "N3: family \"geometry\"'s colour #4080ff does not survive into the SVG")
}

test_n1_refuses_stuck_interior if {
	some msg in p.deny with input as object.union(good, {"stuck": ["hover"]})
	startswith(msg, "N1: 1 interior node(s)")
}

# null is truthy to a bare Rego reference: an unstated in_dot must not admit the node
test_null_in_dot_does_not_fire if {
	inp := object.union(good, {"cases": [{"node": "view", "in_dot": true}, {"node": "fg", "in_dot": null}]})
	p.admitted == {"view"} with input as inp
}

test_all_null_case_withheld_only if {
	inp := object.union(good, {"cases": [{"node": "view", "in_dot": true}, {"node": "fg", "in_dot": null}]})
	some w in p.withheld with input as inp
	w == "N2: fg: in_dot was not measured"
	not "fg" in p.admitted with input as inp
	d := p.deny with input as inp
	every m in d { not contains(m, "\"fg\"") }
}

test_population_flags_null_withheld if {
	inp := object.union(good, {"frames": null, "stuck": null, "render": {"ok": null, "detail": null}})
	w := p.withheld with input as inp
	"N0: frames was not measured" in w
	"N1: stuck was not measured" in w
	some m in w
	startswith(m, "N3: render unverified")
}

# N1 fix (line 41): HEAD's `not c.in_dot` read null as present — no deny, no
# withheld, no admitted: silently nothing
test_null_node_in_dot_is_withheld if {
	inp := object.union(good, {"cases": [{"node": "fg", "in_dot": null}]})
	"N2: fg: in_dot was not measured" in p.withheld with input as inp
}

# N1 fix (line 59): a styled family whose in_dot is null
test_null_family_in_dot_is_withheld if {
	inp := object.union(good, {"families": [{"family": "geometry", "colour": "#4080ff", "in_dot": null, "in_svg": true}]})
	"N3: family geometry: in_dot was not measured" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
}

test_n3_refuses_a_colour_absent_from_the_dot if {
	inp := object.union(good, {"families": [{"family": "geometry", "colour": "#4080ff", "in_dot": false, "in_svg": true}]})
	some m in p.deny with input as inp
	startswith(m, "N3: family \"geometry\" styles as")
}

test_graphviz_absent_is_withheld_beside_admitted if {
	skip := object.union(good, {"render": {"ok": null, "detail": "graphviz `dot` is not installed"}, "families": [{"family": "geometry", "colour": "#4080ff", "in_dot": true, "in_svg": null}]})
	count(p.deny) == 0 with input as skip
	count(p.withheld) == 1 with input as skip
	count(p.admitted) == 2 with input as skip
}
