package el.config_page_test

import data.el.config_page as cp
import rego.v1

good := {"page": "clock-config.qml", "entries": 2, "declared": ["cfg_bloom", "cfg_bloomDefault", "cfg_use24h", "cfg_use24hDefault"], "keys": [
	{"key": "bloom", "type": "Double", "value": true, "default": true},
	{"key": "use24h", "type": "Bool", "value": true, "default": true},
]}

test_admits_clean if {
	count(cp.deny) == 0 with input as {"pages": [good]}
	count(cp.withheld) == 0 with input as {"pages": [good]}
}

test_c0_refuses_no_pages if {
	some msg in cp.deny with input as {"pages": []}
	startswith(msg, "C0:")
}

test_c1_withholds_an_absent_pair if {
	some msg in cp.withheld with input as {"pages": [{"page": "x.qml", "withheld": "x.kcfg or x.qml is absent"}]}
	startswith(msg, "C1:")
}

test_c2_refuses_an_undeclared_value if {
	some msg in cp.deny with input as {"pages": [object.union(good, {"keys": [{"key": "traceLog", "type": "String", "value": false, "default": true}]})]}
	startswith(msg, "C2:")
}

test_c3_refuses_an_undeclared_default if {
	some msg in cp.deny with input as {"pages": [object.union(good, {"keys": [{"key": "speed", "type": "Double", "value": true, "default": false}]})]}
	startswith(msg, "C3:")
}

test_c4_refuses_an_empty_kcfg if {
	some msg in cp.deny with input as {"pages": [{"page": "e.qml", "entries": 0, "declared": [], "keys": []}]}
	startswith(msg, "C4:")
}
