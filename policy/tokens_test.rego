package el.tokens_test

import rego.v1

import data.el.tokens

good := {"variant": "EL-Azure", "present": true, "colors": 44, "alphas": 2, "bad": [],
	"materials": ["base", "emissive", "ghost", "ghost_opacity"]}

test_missing_material_denied if {
	inp := {"cases": [object.union(good, {"materials": ["base", "emissive", "ghost"]})], "current": true, "withheld": []}
	"D5: EL-Azure: material slot ghost_opacity is missing" in tokens.deny with input as inp
	count(tokens.admitted) == 0 with input as inp
}

test_empty_population_denied if {
	count(tokens.deny) == 1 with input as {}
}

test_complete_current_admitted if {
	inp := {"cases": [good], "current": true, "withheld": []}
	count(tokens.deny) == 0 with input as inp
	count(tokens.admitted) == 1 with input as inp
}

test_missing_variant_denied if {
	some m in tokens.deny with input as {"cases": [{"variant": "EL-Azure", "present": false}], "current": true, "withheld": []}
	startswith(m, "D1: EL-Azure")
}

test_bad_leaf_denied if {
	some m in tokens.deny with input as {"cases": [object.union(good, {"bad": ["color.fg"]})], "current": true, "withheld": []}
	startswith(m, "D2: EL-Azure: leaf color.fg")
}

test_missing_alpha_denied if {
	some m in tokens.deny with input as {"cases": [object.union(good, {"alphas": 1})], "current": true, "withheld": []}
	startswith(m, "D3: EL-Azure: 1 of 2")
}

test_stale_file_denied if {
	"D4: catalog/el-openglo.tokens.json is stale; run make_tokens.py" in tokens.deny with input as {"cases": [good], "current": false, "withheld": []}
}

test_unreadable_file_withheld if {
	inp := {"cases": [], "current": null, "withheld": ["token file unreadable: no such file"]}
	count(tokens.withheld) == 1 with input as inp
	count(tokens.deny) == 0 with input as inp
}
