package el.rego_lint_test

import rego.v1

import data.el.rego_lint

bare := {"module": "policy/x.rego", "line": 9, "root": "local", "text": "c.withheld", "value": true}

input_bare := {"module": "policy/x.rego", "line": 3, "root": "input", "text": "input.parsed", "value": true}

rule_ref := {"module": "policy/x.rego", "line": 12, "root": "rule", "text": "helper", "value": false}

float_fmt := {"module": "policy/x.rego", "line": 20, "format": "G2: %.3f", "verbs": ["%.3f"]}

test_absent_population_denied if {
	"R0: no policy file was in the lint's scope" in rego_lint.deny with input as {}
}

test_empty_population_denied if {
	"R0: no policy file was in the lint's scope" in rego_lint.deny with input as {"files": [], "truthy": [], "fixed": []}
}

test_bare_value_reference_denied if {
	some m in rego_lint.deny with input as {"files": ["policy/x.rego"], "truthy": [bare]}
	startswith(m, "T1: policy/x.rego:9 `c.withheld`")
}

test_bare_input_reference_denied if {
	some m in rego_lint.deny with input as {"files": ["policy/x.rego"], "truthy": [input_bare]}
	startswith(m, "T1: policy/x.rego:3")
}

test_rule_reference_admitted if {
	count(rego_lint.deny) == 0 with input as {"files": ["policy/x.rego"], "truthy": [rule_ref]}
}

# the lint's OWN input is judged by value, not truthiness: a null `value` is not a finding
test_null_value_flag_is_not_a_finding if {
	count(rego_lint.deny) == 0 with input as {"files": ["policy/x.rego"], "truthy": [object.union(bare, {"value": null})]}
}

test_negated_value_reference_denied if {
	some m in rego_lint.deny with input as {"files": ["policy/x.rego"], "negated": [bare]}
	startswith(m, "N1: policy/x.rego:9 `not c.withheld`")
}

test_float_verb_denied if {
	some m in rego_lint.deny with input as {"files": ["policy/x.rego"], "fixed": [float_fmt]}
	startswith(m, "F1: policy/x.rego:20")
}

# the declared exemption: withheld and counted, never denied, never silent
test_float_verb_in_the_exempt_file_is_withheld_not_denied if {
	ex := object.union(float_fmt, {"module": "policy/lib/fmt_test.rego", "line": 8})
	inp := {"files": ["policy/lib/fmt_test.rego"], "fixed": [ex]}
	count(rego_lint.deny) == 0 with input as inp
	some m in rego_lint.withheld with input as inp
	startswith(m, "F1: policy/lib/fmt_test.rego:8 exempt — ")
	"policy/lib/fmt_test.rego" in rego_lint.admitted with input as inp
}

# the exemption is by MODULE: the same verb anywhere else still denies
test_the_exemption_does_not_leak_to_another_file if {
	inp := {"files": ["policy/lib/fmt.rego"], "fixed": [object.union(float_fmt, {"module": "policy/lib/fmt.rego"})]}
	some m in rego_lint.deny with input as inp
	startswith(m, "F1: policy/lib/fmt.rego:")
}

test_clean_population_admitted if {
	count(rego_lint.deny) == 0 with input as {"files": ["policy/x.rego"], "truthy": [], "fixed": []}
	"policy/x.rego" in rego_lint.admitted with input as {"files": ["policy/x.rego"], "truthy": [], "fixed": []}
}

test_unparsed_file_withheld_not_admitted if {
	doc := {"files": ["policy/x.rego"], "unreadable": [{"module": "policy/x.rego", "withheld": "opa absent"}]}
	count(rego_lint.withheld) == 1 with input as doc
	count(rego_lint.admitted) == 0 with input as doc
}
