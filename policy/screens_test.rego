package el.screens_test

import data.el.screens as sc
import rego.v1

good := {"file": "clock-EL-Amber.png", "variant": "EL-Amber", "exists": true, "width": 400, "height": 48,
	"modal": "#1f170c", "distinct": 120, "grounds": ["#1f170c", "#140f08"]}

test_admits_clean if {
	count(sc.deny) == 0 with input as {"screens": [good]}
}

test_s0_refuses_no_plan if {
	some msg in sc.deny with input as {"screens": []}
	startswith(msg, "S0:")
}

test_s1_refuses_a_missing_still if {
	some msg in sc.deny with input as {"screens": [{"file": "switcher-EL-Amber.png", "variant": "EL-Amber", "exists": false, "grounds": ["#1f170c", "#140f08"]}]}
	startswith(msg, "S1:")
}

test_s2_refuses_a_blank_still if {
	some msg in sc.deny with input as {"screens": [object.union(good, {"distinct": 1})]}
	startswith(msg, "S2:")
}

test_s3_refuses_the_wrong_ground if {
	some msg in sc.deny with input as {"screens": [object.union(good, {"modal": "#081411"})]}
	startswith(msg, "S3:")
}

test_s3_admits_the_view_ground if {
	count(sc.deny) == 0 with input as {"screens": [object.union(good, {"modal": "#140f08"})]}
}
