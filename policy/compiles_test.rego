package el.compiles_test

import data.el.compiles as p
import rego.v1

good := {"cases": [{"id": "make_font.py", "error": null}, {"id": "cvd_gate.py", "error": null}]}

test_admits_a_tree_that_compiles if {
	count(p.deny) == 0 with input as good
	p.admitted == {"make_font.py", "cvd_gate.py"} with input as good
}

test_k0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "K0:")
}

test_k0_refuses_an_empty_population if {
	some msg in p.deny with input as {"cases": []}
	startswith(msg, "K0:")
}

# NO REAL K1 IS ON RECORD, and for a measured reason: the Python check ran
# py_compile at quiet=2, which swallows the error even under doraise, so it
# could never have reported one (found by the batch-5 selftest arm). The
# refusal is therefore the class itself: a syntax error in a tracked source.
test_k1_refuses_a_source_that_does_not_compile if {
	bad := {"cases": [good.cases[0], {"id": "segment_topology.py", "error": "SyntaxError: invalid syntax"}]}
	some msg in p.deny with input as bad
	msg == "K1: segment_topology.py: SyntaxError: invalid syntax"
	p.admitted == {"make_font.py"} with input as bad
}
