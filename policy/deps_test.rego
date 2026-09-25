package el.deps_test

import data.el.deps as p
import rego.v1

dep(id, d, r) := {"id": id, "dist": lower(id), "files": ["make_palette.py"], "declared": d, "recorded": r}

good := {"manifest": true, "cases": [dep("numpy", true, true), dep("gcalc", false, true)]}

test_admits_declared_and_recorded_imports if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	p.admitted == {"numpy", "gcalc"} with input as good
}

test_d0_refuses_an_empty_walk if {
	some m in p.deny with input as {"manifest": true, "cases": []}
	startswith(m, "D0: the import walk found nothing")
}

test_d0_refuses_an_absent_population if {
	some m in p.deny with input as {}
	startswith(m, "D0:")
}

test_d0_refuses_no_manifest if {
	"D0: no pyproject.toml to account against" in p.deny with input as object.union(good, {"manifest": false})
}

# the qml_sanity case: an import that surfaced inside a function body, undeclared
test_d1_refuses_an_unaccounted_import if {
	inp := {"manifest": true, "cases": [dep("magic", false, false)]}
	"D1: magic is neither declared nor recorded as absent (imported by make_palette.py)" in p.deny with input as inp
	count(p.admitted) == 0 with input as inp
}

test_all_null_case_withheld_only if {
	inp := {"manifest": true, "cases": [{"id": "numpy", "dist": "numpy", "files": [], "declared": null, "recorded": null}]}
	"W: numpy: declared was not measured" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
	count(p.admitted) == 0 with input as inp
}
