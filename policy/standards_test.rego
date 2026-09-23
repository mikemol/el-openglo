package el.standards_test

import data.el.standards as t
import rego.v1

ok_case(attr) := {"module": "cvd_gate", "attr": attr, "imports": true, "error": null, "present": true}

good := {"doc": "STANDARDS.md", "doc_present": true, "cases": [ok_case("apca_Lc"), ok_case("wcag_ratio"), ok_case("SECTORS")]}

test_admits_resolving_appliers if {
	count(t.deny) == 0 with input as good
	count(t.admitted) == 3 with input as good
}

test_t0_refuses_an_absent_population if {
	some msg in t.deny with input as {}
	startswith(msg, "T0:")
}

test_t0_refuses_a_document_citing_nothing if {
	some msg in t.deny with input as {"doc": "STANDARDS.md", "doc_present": true, "cases": []}
	startswith(msg, "T0:")
}

test_t1_refuses_an_absent_document if {
	some msg in t.deny with input as {"doc": "STANDARDS.md", "doc_present": false, "cases": []}
	startswith(msg, "T1:")
}

# the failure this check was written for: the recovery lost cvd_gate's APCA applier
test_t2_refuses_the_lost_apca_applier if {
	lost := {"module": "cvd_gate", "attr": "apca_Lc", "imports": true, "error": null, "present": false}
	some msg in t.deny with input as object.union(good, {"cases": [lost, ok_case("wcag_ratio")]})
	msg == "T2: cvd_gate.apca_Lc: named in STANDARDS.md, absent from the module"
}

test_t2_refuses_a_module_that_will_not_import if {
	broken := {"module": "cvd_gate", "attr": "SECTORS", "imports": false, "error": "SyntaxError", "present": false}
	some msg in t.deny with input as object.union(good, {"cases": [broken]})
	msg == "T2: cvd_gate.SECTORS: module will not import: SyntaxError"
}

# null imports / present are not held: no "absent from the module" T2, nothing admitted
test_null_imports_present_do_not_fire if {
	inp := object.union(good, {"cases": [
		object.union(ok_case("apca_Lc"), {"imports": null, "present": false}),
		object.union(ok_case("wcag_ratio"), {"imports": null}),
		object.union(ok_case("SECTORS"), {"present": null}),
	]})
	d := t.deny with input as inp
	every msg in d {
		not contains(msg, "absent from the module")
	}
	count(t.admitted) == 0 with input as inp
}

# exactly once: an applier with its judged fields null is withheld, never judged
test_all_null_case_withheld_only if {
	inp := object.union(good, {"cases": [object.union(ok_case("apca_Lc"), {"imports": null, "present": null})]})
	w := t.withheld with input as inp
	"cvd_gate.apca_Lc: imports was not measured" in w
	not "cvd_gate.apca_Lc" in t.admitted with input as inp
	d := t.deny with input as inp
	every msg in d {
		not contains(msg, "apca_Lc")
	}
}

# N1 T2 (import): a null imports is not "module will not import"
test_null_imports_not_t2 if {
	inp := object.union(good, {"cases": [object.union(ok_case("apca_Lc"), {"imports": null})]})
	count(t.deny) == 0 with input as inp
}

# N1 T2 (present): a null present under a clean import is withheld, not "absent from the module"
test_null_present_withheld_not_t2 if {
	inp := object.union(good, {"cases": [object.union(ok_case("apca_Lc"), {"present": null})]})
	count(t.deny) == 0 with input as inp
	"cvd_gate.apca_Lc: present was not measured" in t.withheld with input as inp
}
