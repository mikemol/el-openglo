package el.geometry_source_test

import data.el.geometry_source as p
import rego.v1

good := {"authorities": ["segment_topology", "make_segment_display", "display_types"], "cases": [
	{"file": "make_clock.py", "present": true, "reads": ["segment_topology"], "owns": []},
	{"file": "make_notify_marquee.py", "present": true, "reads": ["display_types"], "owns": []},
]}

test_admits_a_de_siloed_tree if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 2 with input as good
}

test_g0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "G0:")
}

# the four-silo state the design log names: a surface with its own literal
# SEGS table and no authority import (the selftest's `SEGS = {"A": ...}`)
test_g2_g3_refuse_a_silo if {
	bad := object.union(good, {"cases": [{"file": "make_wallpaper.py", "present": true, "reads": [], "owns": ["SEGS"]}, good.cases[1]]})
	some m1 in p.deny with input as bad
	m1 == "G3: make_wallpaper.py carries its own stroke table (SEGS) — a re-implementation"
	some m2 in p.deny with input as bad
	startswith(m2, "G2: make_wallpaper.py reads no geometry authority")
	count(p.admitted) == 1 with input as bad
}

# the marquee before display_types was an authority: reads nothing it may
test_g2_refuses_a_surface_reading_no_authority if {
	bad := object.union(good, {"cases": [good.cases[0], {"file": "make_notify_marquee.py", "present": true, "reads": [], "owns": []}]})
	some msg in p.deny with input as bad
	startswith(msg, "G2: make_notify_marquee.py")
}

test_g3_refuses_an_owned_table_even_beside_an_authority if {
	bad := object.union(good, {"cases": [{"file": "make_clock.py", "present": true, "reads": ["segment_topology"], "owns": ["DIGITS"]}]})
	some msg in p.deny with input as bad
	startswith(msg, "G3: make_clock.py")
}

test_g1_refuses_a_vanished_surface if {
	bad := object.union(good, {"cases": [good.cases[0], {"file": "make_plymouth.py", "present": false, "reads": [], "owns": []}]})
	some msg in p.deny with input as bad
	msg == "G1: make_plymouth.py is a declared segment surface and is absent from the tree"
}

# null is truthy to a bare Rego reference: an unstated `present` must not arm G2/G3/admitted
test_null_present_does_not_fire if {
	silo := {"file": "make_wallpaper.py", "present": null, "reads": [], "owns": ["SEGS"]}
	inp := object.union(good, {"cases": [silo, good.cases[1]]})
	count([m | some m in p.deny with input as inp; startswith(m, "G2: make_wallpaper.py")]) == 0
	count([m | some m in p.deny with input as inp; startswith(m, "G3: make_wallpaper.py")]) == 0
	not "make_clock.py" in p.admitted with input as object.union(good, {"cases": [object.union(good.cases[0], {"present": null})]})
}

# exactly-once: a case whose judged fields are all null is withheld, never judged
test_all_null_case_withheld_only if {
	inp := object.union(good, {"cases": [{"file": "make_wallpaper.py", "present": null, "reads": null, "owns": null}, good.cases[1]]})
	w := p.withheld with input as inp
	some m in w
	m == "G4: make_wallpaper.py: present was not measured"
	d := p.deny with input as inp
	count([x | some x in d; contains(x, "make_wallpaper.py")]) == 0
	not "make_wallpaper.py" in p.admitted with input as inp
}

# N1 (G1 `not c.present`): null present is not "absent" and not "present" — withheld
test_null_present_is_withheld_not_absent if {
	inp := object.union(good, {"cases": [{"file": "make_plymouth.py", "present": null, "reads": [], "owns": []}, good.cases[1]]})
	d := p.deny with input as inp
	count([x | some x in d; contains(x, "make_plymouth.py")]) == 0
	w := p.withheld with input as inp
	"G4: make_plymouth.py: present was not measured" in w
}

# a present surface with unmeasured reads/owns is withheld, not silently dropped
test_present_with_null_lists_withheld if {
	inp := object.union(good, {"cases": [{"file": "make_clock.py", "present": true, "reads": null, "owns": null}, good.cases[1]]})
	w := p.withheld with input as inp
	"G4: make_clock.py: reads/owns was not measured" in w
	not "make_clock.py" in p.admitted with input as inp
}
