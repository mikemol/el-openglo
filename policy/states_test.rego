package el.states_test

import data.el.states as p
import rego.v1

ok_case := {"id": "EL-Openglo", "pairs": [
	{"a": "focus", "b": "hover", "q": 1.2},
	{"a": "focus", "b": "sel_bg", "q": 1.4},
	{"a": "hover", "b": "sel_bg", "q": 1.1},
], "grounds": [
	{"state": "focus", "ratio": 9.1},
	{"state": "hover", "ratio": 11.0},
	{"state": "sel_bg", "ratio": 8.0},
]}

test_admits_distinct_states if {
	count(p.deny) == 0 with input as {"cases": [ok_case]}
	p.admitted == {"EL-Openglo"} with input as {"cases": [ok_case]}
}

test_s0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "S0:")
}

# the old selftest's first fixture: focus == hover (75,250,215) is q = 0
test_s1_refuses_identical_focus_and_hover if {
	bad := object.union(ok_case, {"pairs": [{"a": "focus", "b": "hover", "q": 0.0}, ok_case.pairs[1], ok_case.pairs[2]]})
	some msg in p.deny with input as {"cases": [bad]}
	startswith(msg, "S1: EL-Openglo: focus/hover q=0 <")
	count(p.admitted) == 0 with input as {"cases": [bad]}
}

# the old selftest's second fixture: focus 12,28,24 on view 8,20,17 — a ring
# invisible on its ground (ratio measured by check_states --selftest)
test_s2_refuses_a_ring_invisible_on_its_ground if {
	bad := object.union(ok_case, {"grounds": [{"state": "focus", "ratio": 1.07}, ok_case.grounds[1], ok_case.grounds[2]]})
	some msg in p.deny with input as {"cases": [bad]}
	startswith(msg, "S2: EL-Openglo: focus on ground 1.07 <")
}
