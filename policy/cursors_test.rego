package el.cursors_test

import data.el.cursors as c
import rego.v1

tok := {"lit": "#99ffeb", "ground": "#0c1f1a", "ghost": "#3a5a52", "ghost_alpha": 0.45}

good := {"readable": true, "error": null, "link": null, "sizes": [24, 32, 48], "dominant": ["#0c1f1a", "#99ffeb"], "frames": [{"delay": 0, "lit_px": 90, "ghost_px": 0, "pixels": 1}], "frame_counts": {"24": 1, "32": 1, "48": 1}}

frame(i) := {"delay": 120, "lit_px": 40, "ghost_px": 30, "pixels": i}

anim := object.union(good, {"frames": [frame(i) | some i in [1, 2, 3, 4, 5, 6]], "frame_counts": {"24": 6, "32": 6, "48": 6}})

all_names := c.core_shapes | c.core_aliases

entries := {n: e |
	some n in all_names
	e := object.get({"wait": anim, "progress": anim}, n, good)
}

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

test_c8_refuses_stilled_wait if {
	some msg in c.deny with input as with_entry("wait", good)
	startswith(msg, "C8: EL-Openglo wait has 1 frame(s) at 24 px")
}

test_c8_refuses_animated_static_shape if {
	some msg in c.deny with input as with_entry("default", anim)
	startswith(msg, "C8: EL-Openglo default is static")
}

test_c9_refuses_zero_delay if {
	e := object.union(anim, {"frames": [object.union(frame(1), {"delay": 0})]})
	some msg in c.deny with input as with_entry("wait", e)
	startswith(msg, "C9: EL-Openglo wait frame 0")
}

test_c10_refuses_identical_frames if {
	e := object.union(anim, {"frames": [frame(1), frame(1)]})
	some msg in c.deny with input as with_entry("progress", e)
	startswith(msg, "C10: EL-Openglo progress has 1 distinct")
}

test_c11_refuses_ghostless_frame if {
	e := object.union(anim, {"frames": [object.union(frame(1), {"ghost_px": 0})]})
	some msg in c.deny with input as with_entry("wait", e)
	startswith(msg, "C11: EL-Openglo wait frame 0 shows no ghost")
}

test_c11_refuses_unlit_frame if {
	e := object.union(anim, {"frames": [object.union(frame(1), {"lit_px": 0})]})
	some msg in c.deny with input as with_entry("wait", e)
	startswith(msg, "C11: EL-Openglo wait frame 0 shows no lit")
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

# a null readable is not a readable glyph: C3 does not judge its (empty) colours
test_null_readable_does_not_fire if {
	inp := with_entry("zoom-in", object.union(good, {"readable": null, "dominant": []}))
	d := c.deny with input as inp
	every msg in d { not startswith(msg, "C3:") }
}

# a null withheld is "nothing withheld"
test_null_withheld_does_not_fire if {
	inp := {"cases": [object.union(case_with(entries), {"withheld": null})]}
	count(c.withheld) == 0 with input as inp
}

# N1 (C5 `not c.index_theme`): a null index_theme was DENIED as absent
test_null_index_theme_is_withheld_not_denied if {
	inp := {"cases": [object.union(case_with(entries), {"index_theme": null})]}
	"C7: EL-Openglo: [\"index_theme\"] was not measured" in c.withheld with input as inp
	count(c.deny) == 0 with input as inp
	count(c.admitted) == 0 with input as inp
}

# N1 (`measured`: `not c.withheld`): a null withheld dropped the variant from
# every rule, so a real defect was neither denied nor admitted
test_null_withheld_variant_still_judged if {
	inp := {"cases": [object.union(case_with(object.remove(entries, ["pointer"])), {"withheld": null})]}
	"C1: EL-Openglo lacks the core shape pointer" in c.deny with input as inp
}

# a null readable on a core shape was DENIED as missing (C1); it is withheld
test_null_readable_core_shape_is_withheld if {
	inp := with_entry("pointer", object.union(good, {"readable": null}))
	"C7: EL-Openglo: [\"pointer.readable\"] was not measured" in c.withheld with input as inp
	count(c.deny) == 0 with input as inp
}

test_all_null_case_withheld_only if {
	inp := {"cases": [{"id": "EL-Openglo", "theme": null, "withheld": null, "index_theme": null, "tokens": null, "entries": null}]}
	w := c.withheld with input as inp
	some m in w
	startswith(m, "C7: EL-Openglo:")
	count(c.admitted) == 0 with input as inp
	count(c.deny) == 0 with input as inp
}

test_withheld_only if {
	inp := {"cases": [{"id": "EL-Openglo", "withheld": "cannot rasterise"}]}
	count(c.deny) == 0 with input as inp
	count(c.withheld) == 1 with input as inp
	count(c.admitted) == 0 with input as inp
}
