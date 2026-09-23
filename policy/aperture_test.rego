package el.aperture_test

import data.el.aperture as ap
import rego.v1

good := {"variant": "EL-Amber", "expected": {"clear": [152, 126, 90], "half": [203, 169, 121], "covered": [255, 212, 153]},
	"seen": {"clear": [153, 127, 90], "half": [204, 169, 122], "covered": [255, 212, 153]},
	"error": {"clear": 1, "half": 1, "covered": 0}}

test_admits_the_relation if {
	count(ap.deny) == 0 with input as {"variants": [good]}
	count(ap.withheld) == 0 with input as {"variants": [good]}
}

test_a0_refuses_nothing_measured if {
	some msg in ap.deny with input as {"variants": []}
	startswith(msg, "A0:")
}

test_a1_withholds_a_failed_render if {
	some msg in ap.withheld with input as {"variants": [{"variant": "EL-Amber", "expected": good.expected, "withheld": "qml is not installed"}]}
	startswith(msg, "A1:")
}

# a null withheld is "nothing withheld", not a withheld variant
test_null_withheld_does_not_fire if {
	count(ap.withheld) == 0 with input as {"variants": [object.union(good, {"withheld": null})]}
}

# N1 (A2-A4 `not v.withheld`): a null withheld read as a withholding reason and
# dropped the variant from every deny
test_null_withheld_is_still_judged if {
	d := ap.deny with input as {"variants": [object.union(good, {"withheld": null, "error": {"clear": 40, "half": 51, "covered": 103}})]}
	some a in d
	startswith(a, "A2:")
	some b in d
	startswith(b, "A3:")
	some c in d
	startswith(c, "A4:")
}

test_admits_the_good_variant if {
	ap.admitted == {"EL-Amber"} with input as {"variants": [good]}
}

test_all_null_case_withheld_only if {
	i := {"variants": [{"variant": "EL-Amber", "withheld": null, "expected": null, "seen": null, "error": null}]}
	w := ap.withheld with input as i
	some m in w
	startswith(m, "A5: EL-Amber:")
	count(ap.admitted) == 0 with input as i
	count(ap.deny) == 0 with input as i
}

test_null_pip_error_is_withheld_not_passed if {
	i := {"variants": [object.union(good, {"error": {"clear": 1, "half": null, "covered": 0}})]}
	w := ap.withheld with input as i
	w == {"A5: EL-Amber: error [\"half\"] was not measured"}
	count(ap.admitted) == 0 with input as i
	count(ap.deny) == 0 with input as i
}

test_a2_refuses_a_wrong_floor if {
	some msg in ap.deny with input as {"variants": [object.union(good, {"error": {"clear": 40, "half": 1, "covered": 0}})]}
	startswith(msg, "A2:")
}

test_a3_refuses_a_snapping_field if {
	# a field that snaps reads the half pip as the floor: error = half the lit distance
	some msg in ap.deny with input as {"variants": [object.union(good, {"error": {"clear": 1, "half": 51, "covered": 0}})]}
	startswith(msg, "A3:")
}

test_a4_refuses_an_unlit_covered_pip if {
	some msg in ap.deny with input as {"variants": [object.union(good, {"error": {"clear": 1, "half": 1, "covered": 103}})]}
	startswith(msg, "A4:")
}
