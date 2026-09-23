package el.cursors_test

import data.el.cursors as c
import rego.v1

tok := {"lit": "#99ffeb", "ground": "#0c1f1a"}

good := {"readable": true, "error": null, "link": null, "sizes": [24, 32, 48], "dominant": ["#0c1f1a", "#99ffeb"]}

all_names := c.core_shapes | c.core_aliases

entries := {n: good | some n in all_names}

case_with(es) := {"id": "EL-Openglo", "theme": "EL-Openglo-cursors", "index_theme": true, "tokens": tok, "entries": es}

clean := {"cases": [case_with(entries)]}

without(name) := {"cases": [case_with(object.remove(entries, [name]))]}

with_entry(name, e) := {"cases": [case_with(object.union(entries, {name: e}))]}

test_admits_clean if {
	count(c.deny) == 0 with input as clean
	c.admitted == {"EL-Openglo"} with input as clean
}

test_c0_refuses_absent_population if {
	some msg in c.deny with input as {}
	startswith(msg, "C0:")
}

test_c0_refuses_empty_population if {
	some msg in c.deny with input as {"cases": []}
	startswith(msg, "C0:")
}

test_c1_refuses_missing_shape if {
	some msg in c.deny with input as without("pointer")
	msg == "C1: EL-Openglo lacks the core shape pointer"
}

test_c1_refuses_unreadable_shape if {
	some msg in c.deny with input as with_entry("wait", {"readable": false, "error": "not an XCursor file", "link": null, "sizes": [], "dominant": []})
	startswith(msg, "C1:")
}

test_c2_refuses_missing_alias if {
	some msg in c.deny with input as without("left_ptr")
	msg == "C2: EL-Openglo lacks the alias left_ptr"
}

test_c3_refuses_wrong_colour if {
	some msg in c.deny with input as with_entry("default", object.union(good, {"dominant": ["#0c1f1a", "#ff0000"]}))
	startswith(msg, "C3: EL-Openglo default is drawn in #ff0000")
}

test_c3_refuses_blank_glyph if {
	some msg in c.deny with input as with_entry("text", object.union(good, {"dominant": []}))
	contains(msg, "no opaque pixels")
}

test_c3_checks_extra_names_too if {
	some msg in c.deny with input as with_entry("zoom-in", object.union(good, {"dominant": ["#123456"]}))
	startswith(msg, "C3:")
}

test_c4_refuses_missing_size if {
	some msg in c.deny with input as with_entry("move", object.union(good, {"sizes": [32]}))
	startswith(msg, "C4: EL-Openglo move lacks size(s)")
}

test_c5_refuses_no_index if {
	inp := {"cases": [object.union(case_with(entries), {"index_theme": false})]}
	some msg in c.deny with input as inp
	startswith(msg, "C5:")
}

test_c6_refuses_roster_drift if {
	inp := object.union(clean, {"roster_drift": [{"variant": "EL-Amber", "who": "make_inherit", "why": "make_inherit.VARIANTS does not declare it (GRID does)"}]})
	some msg in c.deny with input as inp
	startswith(msg, "C6: EL-Amber make_inherit")
}

test_c6_admits_no_drift if {
	inp := object.union(clean, {"roster_drift": []})
	count(c.deny) == 0 with input as inp
}

test_withheld_only if {
	inp := {"cases": [{"id": "EL-Openglo", "withheld": "cannot rasterise"}]}
	count(c.deny) == 0 with input as inp
	count(c.withheld) == 1 with input as inp
	count(c.admitted) == 0 with input as inp
}
