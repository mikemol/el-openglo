# Every rule has a REFUSING case and an ADMITTING case (`opa test policy/`).
package el.chrome_zips_test

import data.el.chrome_zips
import rego.v1

good(v) := {"variant": v, "exists": true, "root_manifest": true, "parses": true, "manifest_version": 3}

clean := {"dist": true, "cases": [good("EL-Openglo"), good("EL-Amber")]}

test_admits_clean if {
	count(chrome_zips.deny) == 0 with input as clean
	chrome_zips.admitted == {"EL-Openglo", "EL-Amber"} with input as clean
}

test_c0_refuses_empty if {
	some msg in chrome_zips.deny with input as {"dist": true, "cases": []}
	startswith(msg, "C0:")
}

test_c0_refuses_absent_population if {
	some msg in chrome_zips.deny with input as {}
	startswith(msg, "C0:")
}

test_absent_dist_is_withheld_not_denied if {
	inp := {"dist": false, "cases": [{"variant": "EL-Openglo", "exists": false}]}
	count(chrome_zips.deny) == 0 with input as inp
	count(chrome_zips.withheld) == 1 with input as inp
	count(chrome_zips.admitted) == 0 with input as inp
}

test_c1_refuses_a_missing_zip if {
	inp := {"dist": true, "cases": [good("EL-Openglo"), {"variant": "EL-Amber", "exists": false}]}
	some msg in chrome_zips.deny with input as inp
	startswith(msg, "C1: EL-Amber")
}

test_c2_refuses_a_nested_manifest if {
	inp := {"dist": true, "cases": [{"variant": "EL-Amber", "exists": true, "root_manifest": false}]}
	some msg in chrome_zips.deny with input as inp
	startswith(msg, "C2: EL-Amber")
}

test_c3_refuses_manifest_v2 if {
	inp := {"dist": true, "cases": [{"variant": "EL-Amber", "exists": true, "root_manifest": true, "parses": true, "manifest_version": 2}]}
	some msg in chrome_zips.deny with input as inp
	startswith(msg, "C3: EL-Amber")
}

test_c3_refuses_an_unparsed_manifest if {
	inp := {"dist": true, "cases": [{"variant": "EL-Amber", "exists": true, "root_manifest": true, "parses": false, "manifest_version": null}]}
	some msg in chrome_zips.deny with input as inp
	startswith(msg, "C3: EL-Amber")
}
