package el.chrome_test

import data.el.chrome as p
import rego.v1

# a trimmed real case (--json, 2026-09-23: EL-Amber, two of its ten colours)
amber := {"id": "EL-Amber", "error": null, "manifest_version": 3, "name": "EL Openglo (EL-Amber)", "roundtrips": true, "colors": [
	{"key": "frame", "value": [31, 23, 12], "ints": true},
	{"key": "ntp_text", "value": [255, 212, 153], "ints": true},
]}

good := {"roster": ["EL-Amber"], "snapshot": ["EL-Amber"], "error": null, "withheld": null, "cases": [amber]}

with_colour(x) := object.union(good, {"cases": [object.union(amber, {"colors": [x]})]})

test_admits_a_valid_manifest if {
	count(p.deny) == 0 with input as good
	p.admitted == {"EL-Amber"} with input as good
}

test_b0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "B0: no manifests were measured")
}

test_b0_withholds_a_missing_third_party_module if {
	w := {"roster": [], "snapshot": [], "cases": [], "error": null, "withheld": "needs PIL, which is not installed here"}
	count(p.deny) == 0 with input as w
	some msg in p.withheld with input as w
	contains(msg, "needs PIL")
}

test_b0_refuses_a_stray_snapshot_member if {
	bad := object.union(good, {"snapshot": ["EL-Amber", "EL-Old"]})
	some msg in p.deny with input as bad
	msg == "B0: EL-Old: present in the schemes snapshot but GRID does not declare it"
}

# the real failure recorded in check_chrome's docstring (W61 B2): EL-Amber.colors
# deleted — the old listing-based population went 6 of 6 to 5 of 5, exit 0. Under
# the roster the variant is still measured, and parse_scheme's raise is denied.
test_b1_refuses_a_declared_variant_whose_scheme_is_gone if {
	bad := {"roster": ["EL-Amber"], "snapshot": [], "error": null, "withheld": null, "cases": [{"id": "EL-Amber", "error": "FileNotFoundError: EL-Amber.colors", "manifest_version": null, "name": null, "colors": null, "roundtrips": null}]}
	some msg in p.deny with input as bad
	msg == "B1: EL-Amber: FileNotFoundError: EL-Amber.colors"
	some m2 in p.deny with input as bad
	m2 == "B0: EL-Amber: declared by GRID but absent from the schemes snapshot"
}

test_b2_refuses_manifest_v2 if {
	bad := object.union(good, {"cases": [object.union(amber, {"manifest_version": 2})]})
	some msg in p.deny with input as bad
	msg == "B2: EL-Amber: manifest_version is 2, not 3"
}

test_b2_refuses_no_name if {
	bad := object.union(good, {"cases": [object.union(amber, {"name": ""})]})
	some msg in p.deny with input as bad
	msg == "B2: EL-Amber: no name"
}

test_b3_refuses_empty_colors if {
	bad := object.union(good, {"cases": [object.union(amber, {"colors": []})]})
	some msg in p.deny with input as bad
	msg == "B3: EL-Amber: theme.colors is missing or empty"
}

# no real B4 denial is recorded; these are the shapes the docstring names:
# a token that failed to parse (None, a string), and a channel out of range
test_b4_refuses_an_out_of_range_channel if {
	some msg in p.deny with input as with_colour({"key": "frame", "value": [1, 2, 999], "ints": true})
	msg == "B4: EL-Amber: colour 'frame' is [1, 2, 999], not an RGB triple in 0..255"
}

test_b4_refuses_a_string_colour if {
	some msg in p.deny with input as with_colour({"key": "frame", "value": "#fff", "ints": false})
	msg == "B4: EL-Amber: colour 'frame' is #fff, not an RGB triple in 0..255"
}

test_b4_refuses_a_null_colour if {
	some msg in p.deny with input as with_colour({"key": "frame", "value": null, "ints": false})
	startswith(msg, "B4: EL-Amber: colour 'frame'")
}

test_b4_refuses_a_float_channel if {
	some msg in p.deny with input as with_colour({"key": "frame", "value": [1, 2, 3], "ints": false})
	startswith(msg, "B4: EL-Amber: colour 'frame'")
}

test_b5_refuses_an_unserialisable_manifest if {
	bad := object.union(good, {"cases": [object.union(amber, {"roundtrips": false})]})
	some msg in p.deny with input as bad
	msg == "B5: EL-Amber: the manifest does not serialise as JSON"
}
