package el.gcalc_api_test

import data.el.gcalc_api as p
import rego.v1

good := {"present": true, "names": [
	{"name": "netlist", "module": "gcalc.solver.netlist", "defined": true, "why": ""},
	{"name": "freeze", "module": "gcalc.solver.driver", "defined": true, "why": ""},
], "callers": [{"file": "scripts/check_nodal.py", "line": 60, "name": "netlist", "declared": true}]}

test_admits_a_faithful_adapter if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 3 with input as good
}

test_g0_refuses_an_empty_population if {
	some msg in p.deny with input as {"present": true, "names": [], "callers": []}
	startswith(msg, "G0:")
}

test_g0_absent_population_is_empty if {
	some msg in p.deny with input as {}
	startswith(msg, "G0:")
}

# the failure that put the gate red: the sibling moved a name
test_g1_refuses_a_name_the_sibling_no_longer_defines if {
	bad := object.union(good, {"names": [{"name": "freeze", "module": "gcalc.solver", "defined": false, "why": "gcalc.solver defines no freeze"}]})
	some msg in p.deny with input as bad
	startswith(msg, "G1: gcalc_api names freeze from gcalc.solver")
	not "freeze" in p.admitted with input as bad
}

test_g2_refuses_an_undeclared_caller_read if {
	bad := object.union(good, {"callers": [{"file": "scripts/check_nodal.py", "line": 61, "name": "elimination_tree", "declared": false}]})
	some msg in p.deny with input as bad
	startswith(msg, "G2: scripts/check_nodal.py:61 reads elimination_tree")
}

# an absent sibling is withheld, never read as the names resolving or failing
test_absent_sibling_is_withheld_not_judged if {
	absent := {"present": false, "names": [{"name": "netlist", "module": "gcalc.solver.netlist", "defined": false, "why": ""}], "callers": []}
	"W: the gcalculus sibling is absent; its names were not resolved (a SKIP, never a pass)" in p.withheld with input as absent
	count([m | some m in p.deny with input as absent; startswith(m, "G1:")]) == 0
	count(p.admitted) == 0 with input as absent
}
