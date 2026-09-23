package el.ghost_balance_test

import data.el.ghost_balance as p
import rego.v1

# the real tree's EL-Openglo and EL-Openglo-Lit rows (--compare, 2026-09-23)
good := {"cases": [
	{"id": "EL-Openglo", "scan": 3.955, "solve": 3.991, "ideal": 3.996, "skew": 1.0022},
	{"id": "EL-Openglo-Lit", "scan": 3.381, "solve": 3.381, "ideal": 3.415, "skew": 1.0200},
]}

test_admits_a_balanced_solve if {
	count(p.deny) == 0 with input as good
	p.admitted == {"EL-Openglo", "EL-Openglo-Lit"} with input as good
}

test_b0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "B0:")
}

test_b1_refuses_a_solve_that_loses_to_the_scan if {
	bad := {"cases": [object.union(good.cases[0], {"solve": 3.900}), good.cases[1]]}
	some msg in p.deny with input as bad
	msg == "B1: EL-Openglo: solved worst side 3.9000 < scanned 3.9550"
	p.admitted == {"EL-Openglo-Lit"} with input as bad
}

# the old selftest's refusing fixture: a ghost at t=0.02 along lit->ground is
# nearly the lit colour, one side ~1.0 and the other the whole span — the skew
# the scan's silence could never show, and the gate must refuse
test_b2_refuses_an_off_balance_ghost if {
	bad := {"cases": [good.cases[0], object.union(good.cases[1], {"skew": 11.4})]}
	some msg in p.deny with input as bad
	startswith(msg, "B2: EL-Openglo-Lit: sides differ by 11.4000x")
}

test_b2_the_bound_is_inclusive if {
	count(p.deny) == 0 with input as {"cases": [object.union(good.cases[0], {"skew": 1.06})]}
}
