package el.readme_test

import data.el.readme as rd
import rego.v1

items := [
	{"kind": "emitter", "name": "make_gtk", "named": true},
	{"kind": "variant", "name": "EL-Amber", "named": true},
	{"kind": "picture", "name": "strip.png", "named": true},
	{"kind": "symbol", "name": "⊕GTK", "named": true},
]

frags := [{"name": "gallery.md", "current": true}]

good := {"readme": true, "items": items, "fragments": frags}

test_admits_a_covering_readme if {
	count(rd.deny) == 0 with input as good
}

test_r0_refuses_an_absent_population if {
	some msg in rd.deny with input as {}
	startswith(msg, "R0:")
}

test_r0_refuses_a_missing_kind if {
	some msg in rd.deny with input as object.union(good, {"items": [i | some i in items; i.kind != "picture"]})
	msg == "R0: no picture was measured"
}

test_r1_refuses_no_readme if {
	some msg in rd.deny with input as object.union(good, {"readme": false})
	startswith(msg, "R1:")
}

test_r2_refuses_an_unnamed_item if {
	some msg in rd.deny with input as object.union(good, {"items": array.concat(items, [{"kind": "emitter", "name": "make_union", "named": false}])})
	msg == "R2: README.md does not name emitter make_union"
}

test_r3_refuses_a_stale_fragment if {
	some msg in rd.deny with input as object.union(good, {"fragments": [{"name": "gallery.md", "current": false}]})
	startswith(msg, "R3:")
}

test_r4_refuses_roster_drift if {
	inp := object.union(good, {"roster_drift": [{"variant": "EL-Amber", "who": "render_screens", "why": "render_screens.VARIANTS does not declare it (GRID does)"}]})
	some msg in rd.deny with input as inp
	startswith(msg, "R4: EL-Amber render_screens")
}

test_r4_admits_no_drift if {
	count(rd.deny) == 0 with input as object.union(good, {"roster_drift": []})
}

test_r3_refuses_no_fragments if {
	some msg in rd.deny with input as object.union(good, {"fragments": []})
	msg == "R3: no fragment was measured"
}
