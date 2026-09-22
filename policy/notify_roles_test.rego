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
