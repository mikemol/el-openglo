package el.selection_contrast_test

import data.el.selection_contrast as p
import rego.v1

bg := [120, 200, 185]

case(id, r) := {"id": id, "scheme": split(id, "/")[0], "key": split(id, "/")[1], "fg": [8, 20, 17], "bg": bg, "ratio": r, "why": null}

good := {"roster": ["EL-Openglo", "EL-Openglo-Lit"], "keys": ["ForegroundNormal", "ForegroundNegative"], "cases": [
	case("EL-Openglo/ForegroundNormal", 7.1),
	case("EL-Openglo/ForegroundNegative", 3.4),
	case("EL-Openglo-Lit/ForegroundNormal", 6.8),
	case("EL-Openglo-Lit/ForegroundNegative", 3.33),
]}

test_admits_a_legible_tree if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 4 with input as good
}

test_s0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "S0:")
}

# the W65 probe: a renamed [Colors:Selection] header in one scheme — the old
# check went 30 of 30 -> 25 of 25, exit 0; the reader now returns it as missing
test_s0_refuses_a_scheme_whose_selection_section_is_unreadable if {
	why := "[Colors:Selection] BackgroundNormal is absent"
	lost := [object.union(c, {"ratio": null, "fg": null, "bg": null, "why": why}) | some c in good.cases; c.scheme == "EL-Openglo-Lit"]
	kept := [c | some c in good.cases; c.scheme == "EL-Openglo"]
	bad := object.union(good, {"cases": array.concat(kept, lost)})
	some msg in p.deny with input as bad
	msg == "S0: EL-Openglo-Lit/ForegroundNormal: [Colors:Selection] BackgroundNormal is absent"
	p.admitted == {"EL-Openglo/ForegroundNormal", "EL-Openglo/ForegroundNegative"} with input as bad
}

test_s0_refuses_a_shrunk_population if {
	bad := object.union(good, {"cases": array.slice(good.cases, 0, 2)})
	some msg in p.deny with input as bad
	msg == "S0: 2 of 4 declared pairs measured (2 schemes x 2 keys)"
}

# the real W10 failure: EL-Openglo-Lit's negative-on-selection at 2.94:1
test_s1_refuses_a_pair_below_the_floor if {
	bad := object.union(good, {"cases": array.concat(array.slice(good.cases, 0, 3), [case("EL-Openglo-Lit/ForegroundNegative", 2.94)])})
	some msg in p.deny with input as bad
	startswith(msg, "S1: EL-Openglo-Lit/ForegroundNegative:")
}

# ...which was PINNED at 2.94 while infeasible: admitted at the pin, refused once it moved
test_s2_a_pin_holds_at_its_ratio if {
	at_pin := object.union(good, {"cases": array.concat(array.slice(good.cases, 0, 3), [case("EL-Openglo-Lit/ForegroundNegative", 2.94)])})
	count(p.deny) == 0 with input as at_pin with p.pinned as {"EL-Openglo-Lit/ForegroundNegative": 2.94}
}

test_s2_refuses_a_pin_that_moved if {
	some msg in p.deny with input as good with p.pinned as {"EL-Openglo-Lit/ForegroundNegative": 2.94}
	startswith(msg, "S2: EL-Openglo-Lit/ForegroundNegative: 3.33:1")
}
