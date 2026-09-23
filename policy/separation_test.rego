package el.separation_test

import data.el.separation as p
import rego.v1

case(v, pair, d) := {"id": sprintf("%s/%s", [v, pair]), "variant": v, "pair": pair, "a": "x", "b": "y", "dE": d, "view": "deuteranomaly", "why": null}

good := {"variants": ["EL-Openglo", "EL-Azure"], "enforced": ["neg-pos", "neg-neu"], "surfaced": ["focus"], "floor": 11.0, "cases": [
	case("EL-Openglo", "neg-pos", 14.2),
	case("EL-Openglo", "neg-neu", 9.1),
	case("EL-Azure", "neg-pos", 12.7),
	case("EL-Azure", "neg-neu", 8.8),
]}

test_admits_separated_pairs if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 4 with input as good
}

test_d0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "D0:")
}

test_d0_refuses_a_shrunk_population if {
	bad := object.union(good, {"cases": array.slice(good.cases, 0, 3)})
	some msg in p.deny with input as bad
	msg == "D0: 3 of 4 declared pairs measured (2 variants x 2 pairs)"
}

test_d0_refuses_an_unreadable_pair if {
	lost := object.union(good.cases[3], {"dE": null, "view": null, "why": "the variant carries no token 'neutral'"})
	bad := object.union(good, {"cases": array.concat(array.slice(good.cases, 0, 3), [lost])})
	some msg in p.deny with input as bad
	msg == "D0: EL-Azure/neg-neu: the variant carries no token 'neutral'"
}

# no real enforced-pair violation is on record — the recorded defect is that
# audit_variant had NO CALLER — so the refusal is the old selftest's fixture:
# every enforced pair drawn in one grey, dE 0 (a whole number: no %!f)
test_d1_refuses_identical_colours if {
	bad := object.union(good, {"cases": [object.union(c, {"dE": 0}) | some c in good.cases]})
	msgs := p.deny with input as bad
	count(msgs) == 4
	"D1: EL-Openglo/neg-pos: dE 0.0 < 8.8 (deuteranomaly)" in msgs
	every msg in msgs {
		not contains(msg, "%!")
	}
}

test_d1_the_floor_is_inclusive if {
	at := object.union(good, {"cases": [object.union(c, {"dE": 8.8}) | some c in good.cases]})
	count(p.deny) == 0 with input as at
}
