package el.atomic_writes_test

import rego.v1

import data.el.atomic_writes

atomic := {"module": "make_x", "line": 1, "kind": "atomic_write", "atomic": true, "exempt": false, "reason": null}

plain := {"module": "make_x", "line": 2, "kind": "open", "atomic": false, "exempt": false, "reason": null}

exempt_ok := {"module": "make_x", "line": 3, "kind": "open", "atomic": false, "exempt": true, "reason": "a private tempdir"}

exempt_bare := {"module": "make_x", "line": 4, "kind": "open", "atomic": false, "exempt": true, "reason": ""}

test_absent_population_denied if {
	"A0: no write site was measured" in atomic_writes.deny with input as {}
}

test_empty_population_denied if {
	"A0: no write site was measured" in atomic_writes.deny with input as {"cases": [], "helper_present": true}
}

test_plain_write_denied if {
	some m in atomic_writes.deny with input as {"cases": [atomic, plain], "helper_present": true}
	startswith(m, "A1: make_x.py:2")
}

test_exempt_without_reason_denied if {
	some m in atomic_writes.deny with input as {"cases": [exempt_bare], "helper_present": true}
	startswith(m, "A2: make_x.py:4")
}

# a null exempt is not an exemption: no A2, and not admitted as exempt
test_null_exempt_does_not_fire if {
	i := {"cases": [object.union(exempt_bare, {"exempt": null})], "helper_present": true}
	d := atomic_writes.deny with input as i
	every m in d { not startswith(m, "A2:") }
	count(atomic_writes.admitted) == 0 with input as i
}

# a null atomic is not an atomic write: the site is not admitted
test_null_atomic_does_not_fire if {
	i := {"cases": [object.union(plain, {"atomic": null})], "helper_present": true}
	count(atomic_writes.admitted) == 0 with input as i
}

test_missing_helper_denied if {
	"A3: emitters.atomic_write is absent — the admitted form names nothing" in atomic_writes.deny with input as {"cases": [atomic], "helper_present": false}
}

test_atomic_and_reasoned_exempt_admitted if {
	count(atomic_writes.deny) == 0 with input as {"cases": [atomic, exempt_ok], "helper_present": true}
	count(atomic_writes.admitted) == 2 with input as {"cases": [atomic, exempt_ok], "helper_present": true}
}
