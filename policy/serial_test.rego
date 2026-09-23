# Every rule has a REFUSING case and an ADMITTING case. The shapes mirror
# `scripts/read_serial.py --json`; the four logs under catalog/fixtures/serial/
# exercise the same rules end to end through `scripts/opa_gate.py serial LOG`.
package el.serial_test

import data.el.serial
import rego.v1

p2 := {
	"boot": "b-1", "probe": "P2", "withheld": [],
	"kinds": {"el.ident": 1, "el.session": 1, "el.settled": 1, "el.journal": 1, "el.file": 1, "el.done": 1},
	"done": {"seq": 20, "probe": "P2", "records": 20},
}

test_admits_a_complete_p2 if {
	count(serial.deny) == 0 with input as {"cases": [p2]}
	count(serial.withheld) == 0 with input as {"cases": [p2]}
	serial.admitted == {"b-1"} with input as {"cases": [p2]}
}

test_s0_refuses_empty_population if {
	count(serial.deny) == 1 with input as {"cases": []}
}

test_s0_refuses_absent_population if {
	count(serial.deny) == 1 with input as {}
}

test_s1_refuses_a_boot_without_done if {
	c := object.union(p2, {"done": null})
	some msg in serial.deny with input as {"cases": [c]}
	startswith(msg, "S1: boot b-1")
	count(serial.admitted) == 0 with input as {"cases": [c]}
}

test_s2_refuses_an_unknown_probe if {
	c := object.union(p2, {"probe": "P9"})
	some msg in serial.deny with input as {"cases": [c]}
	startswith(msg, "S2: boot b-1")
}

test_s3_refuses_a_missing_required_kind if {
	# object.union merges nested objects, so drop `kinds` before replacing it
	c := object.union(object.remove(p2, ["kinds"]), {"kinds": {"el.ident": 1, "el.session": 1, "el.settled": 1, "el.journal": 1, "el.done": 1}})
	some msg in serial.deny with input as {"cases": [c]}
	msg == "S3: boot b-1 (probe P2) sent no el.file"
}

test_s3_admits_p3_without_session_kinds if {
	c := {"boot": "b-3", "probe": "P3", "withheld": [], "kinds": {"el.ident": 1, "el.journal": 1, "el.done": 1}, "done": {"seq": 9, "probe": "P3", "records": 9}}
	serial.admitted == {"b-3"} with input as {"cases": [c]}
}

test_s4_refuses_a_probe_mismatch if {
	c := object.union(p2, {"done": {"seq": 20, "probe": "P4", "records": 20}})
	some msg in serial.deny with input as {"cases": [c]}
	startswith(msg, "S4: boot b-1")
}

test_gap_is_withheld_not_denied if {
	c := object.union(p2, {"withheld": ["gap: seq 1 missing"]})
	count(serial.deny) == 0 with input as {"cases": [c]}
	serial.withheld == {"boot b-1: gap: seq 1 missing"} with input as {"cases": [c]}
	count(serial.admitted) == 0 with input as {"cases": [c]}
}

test_log_level_withheld_beside_an_admitted_boot if {
	inp := {"cases": [p2], "withheld": ["line 7: malformed frame"]}
	serial.withheld == {"log: line 7: malformed frame"} with input as inp
	serial.admitted == {"b-1"} with input as inp
}
