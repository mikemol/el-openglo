package el.notify_roles_test

import data.el.notify_roles as nr
import rego.v1

good := {"roles": {"IdRole": 0, "UrgencyRole": 29, "PercentageRole": 19}, "needed": ["IdRole", "UrgencyRole", "PercentageRole"],
	"stub_roles": ["IdRole", "UrgencyRole", "PercentageRole"], "methods": ["invokeAction", "expire"], "enums": {}}

test_admits_a_declared_and_modelled_contract if {
	count(nr.deny) == 0 with input as good
	count(nr.withheld) == 0 with input as good
}

test_n0_refuses_no_roles if {
	# object.union merges nested objects, so an empty roles map is stated outright
	some msg in nr.deny with input as {"roles": {}, "needed": [], "stub_roles": [], "methods": ["invokeAction"]}
	startswith(msg, "N0:")
}

test_n1_withholds_an_absent_module if {
	some msg in nr.withheld with input as {"withheld": "no qmltypes", "roles": {}, "needed": ["IdRole"]}
	startswith(msg, "N1:")
}

# null is truthy to a bare Rego reference: withheld: null is not a withholding
test_null_withheld_does_not_fire if {
	count(nr.withheld) == 0 with input as object.union(good, {"withheld": null})
}

test_all_null_case_withheld_only if {
	inp := {"withheld": null, "roles": null, "needed": null, "stub_roles": null, "methods": null}
	count(nr.deny) == 0 with input as inp
	w := nr.withheld with input as inp
	w == {"N0: roles was not measured", "N0: needed was not measured", "N0: stub_roles was not measured", "N0: methods was not measured"}
}

# N1 fix (lines 15/34/46/55): HEAD's `not input.withheld` read a null reason as
# a withholding, so every rule went silent and nothing was withheld either
test_null_withheld_still_judges if {
	inp := object.union(good, {"withheld": null, "needed": ["IdRole", "HintsRole"]})
	"N2: the host's model does not declare HintsRole" in nr.deny with input as inp
}

test_null_withheld_still_judges_n4 if {
	inp := object.union(good, {"withheld": null, "methods": ["expire"]})
	"N4: the model has no invokeAction" in nr.deny with input as inp
}

test_null_withheld_still_refuses_no_roles if {
	inp := {"withheld": null, "roles": {}, "needed": [], "stub_roles": [], "methods": ["invokeAction"]}
	some m in nr.deny with input as inp
	startswith(m, "N0:")
}

test_null_methods_is_withheld_not_denied if {
	inp := object.union(good, {"methods": null})
	"N0: methods was not measured" in nr.withheld with input as inp
	not "N4: the model has no invokeAction" in nr.deny with input as inp
}

test_n2_refuses_a_role_the_host_lacks if {
	some msg in nr.deny with input as object.union(good, {"needed": ["IdRole", "HintsRole"]})
	startswith(msg, "N2:")
}

test_n3_refuses_a_role_the_stub_lacks if {
	some msg in nr.deny with input as object.union(good, {"stub_roles": ["IdRole"]})
	startswith(msg, "N3:")
}

test_n4_refuses_no_invoke_action if {
	some msg in nr.deny with input as object.union(good, {"methods": ["expire"]})
	startswith(msg, "N4:")
}
