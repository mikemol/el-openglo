package el.st_api_test

import data.el.st_api as p
import rego.v1

good := {"module_present": true, "cases": [
	{"symbol": "GEOM16", "files": ["make_clock.py"], "exported": true},
	{"symbol": "project", "files": ["display_types.py", "make_clock.py"], "exported": true},
]}

test_admits_an_exported_api if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 2 with input as good
}

test_a0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "A0:")
}

test_a0_refuses_an_empty_search if {
	some msg in p.deny with input as {"module_present": true, "cases": []}
	startswith(msg, "A0:")
}

test_a1_refuses_an_absent_module if {
	bad := {"module_present": false, "cases": [{"symbol": "GEOM16", "files": ["a.py"], "exported": false}]}
	some msg in p.deny with input as bad
	msg == "A1: segment_topology.py is absent"
	count(p.admitted) == 0 with input as bad
}

# the recovery's real gap: consumers referenced the 22-segment geometry the
# module did not define
test_a2_refuses_the_missing_22_segment_geometry if {
	bad := object.union(good, {"cases": array.concat(good.cases, [{"symbol": "GEOM22", "files": ["display_types.py"], "exported": false}])})
	some msg in p.deny with input as bad
	msg == "A2: ST.GEOM22 is not exported (referenced by display_types.py)"
	count(p.admitted) == 2 with input as bad
}

# null module_present is not held: no A2 over a module never read, nothing admitted
test_null_module_present_does_not_fire if {
	inp := {"module_present": null, "cases": [{"symbol": "GEOM22", "files": ["display_types.py"], "exported": false}, good.cases[0]]}
	d := p.deny with input as inp
	every msg in d {
		not startswith(msg, "A2:")
	}
	count(p.admitted) == 0 with input as inp
}

# null exported is not held: the symbol is not admitted
test_null_exported_does_not_admit if {
	inp := object.union(good, {"cases": [object.union(good.cases[0], {"exported": null})]})
	count(p.admitted) == 0 with input as inp
}
