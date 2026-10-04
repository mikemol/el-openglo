package el.render_constants_test

import data.el.render_constants as p
import rego.v1

prop(name, configurable, disposition) := {"name": name, "type": "real", "literal": "1.0", "line": 7, "configurable": configurable, "disposition": disposition}

good := {"cases": [{"template": "t.qml", "keys": [], "props": [
	prop("glow", true, null),
	prop("timeStr", false, "STATE"),
	prop("segLen", false, "MOUNT"),
	prop("fill", false, "WITHHELD:derived from the panel height"),
]}], "registry_stale": []}

test_admits_configured_state_mount_and_withheld_with_reason if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 4 with input as good
}

test_c0_refuses_an_empty_population if {
	some msg in p.deny with input as {"cases": [], "registry_stale": []}
	startswith(msg, "C0:")
}

test_c0_absent_population_is_empty if {
	some msg in p.deny with input as {}
	startswith(msg, "C0:")
}

# the failure the check exists for: a render value nothing configures and nobody classified
test_c1_refuses_an_undeclared_literal if {
	bad := {"cases": [{"template": "t.qml", "keys": [], "props": [prop("gamma", false, null)]}], "registry_stale": []}
	some msg in p.deny with input as bad
	startswith(msg, "C1: t.qml:7 gamma = 1.0")
	not "t.qml:gamma" in p.admitted with input as bad
}

test_c2_refuses_an_unknown_kind if {
	bad := {"cases": [{"template": "t.qml", "keys": [], "props": [prop("x", false, "LATER")]}], "registry_stale": []}
	some msg in p.deny with input as bad
	startswith(msg, "C2:")
}

test_c2_refuses_a_withheld_without_a_reason if {
	bad := {"cases": [{"template": "t.qml", "keys": [], "props": [prop("x", false, "WITHHELD")]}], "registry_stale": []}
	some msg in p.deny with input as bad
	startswith(msg, "C2:")
	not "t.qml:x" in p.admitted with input as bad
}

test_c3_refuses_a_stale_registry_entry if {
	some msg in p.deny with input as object.union(good, {"registry_stale": ["t.qml:ghost"]})
	startswith(msg, "C3:")
}

# OPEN is debt: it is withheld (counted, printed) beside admitted properties, never denied, never admitted
test_open_is_debt_not_a_pass if {
	inp := {"cases": [{"template": "t.qml", "keys": [], "props": [prop("glow", true, null), prop("scale", false, "OPEN:W268")]}], "registry_stale": []}
	count(p.deny) == 0 with input as inp
	some msg in p.withheld with input as inp
	startswith(msg, "O: t.qml scale is OPEN")
	not "t.qml:scale" in p.admitted with input as inp
	"t.qml:glow" in p.admitted with input as inp
}

test_unmeasured_registry_is_withheld if {
	inp := {"cases": good.cases}
	"O: registry_stale was not measured" in p.withheld with input as inp
}
