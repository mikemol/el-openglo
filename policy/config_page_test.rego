package el.config_page_test

import data.el.config_page as cp
import rego.v1

good := {"page": "clock-config.qml", "entries": 2, "declared": ["cfg_bloom", "cfg_bloomDefault", "cfg_use24h", "cfg_use24hDefault"], "keys": [
	{"key": "bloom", "type": "Double", "value": true, "default": true},
	{"key": "use24h", "type": "Bool", "value": true, "default": true},
]}

good_mount := {"mount": "clock", "has_page": true, "stray": [], "params": [
	{"param": "bloom", "declared": "exposed", "spelling": "bloom", "in_kcfg": true, "on_page": true},
	{"param": "fill", "declared": "withheld", "reason": "SegmentChar's stroke is the substrate's"},
]}

good_display := {"params": ["bloom", "fill"], "mounts": [good_mount]}

with_mount(m) := {"pages": [good], "display": {"params": ["bloom", "fill"], "mounts": [m]}}

test_admits_clean if {
	count(cp.deny) == 0 with input as {"pages": [good], "display": good_display}
	count(cp.withheld) == 0 with input as {"pages": [good], "display": good_display}
}

test_c0_refuses_no_pages if {
	some msg in cp.deny with input as {"pages": [], "display": good_display}
	startswith(msg, "C0:")
}

test_c1_withholds_an_absent_pair if {
	some msg in cp.withheld with input as {"pages": [{"page": "x.qml", "withheld": "x.kcfg or x.qml is absent"}], "display": good_display}
	startswith(msg, "C1:")
}

# a null withheld is "nothing withheld", not a withheld page
test_null_withheld_does_not_fire if {
	count(cp.withheld) == 0 with input as {"pages": [object.union(good, {"withheld": null})], "display": good_display}
}

test_c2_refuses_an_undeclared_value if {
	some msg in cp.deny with input as {"pages": [object.union(good, {"keys": [{"key": "traceLog", "type": "String", "value": false, "default": true}]})], "display": good_display}
	startswith(msg, "C2:")
}

test_c3_refuses_an_undeclared_default if {
	some msg in cp.deny with input as {"pages": [object.union(good, {"keys": [{"key": "speed", "type": "Double", "value": true, "default": false}]})], "display": good_display}
	startswith(msg, "C3:")
}

test_c4_refuses_an_empty_kcfg if {
	some msg in cp.deny with input as {"pages": [{"page": "e.qml", "entries": 0, "declared": [], "keys": []}], "display": good_display}
	startswith(msg, "C4:")
}

test_d0_refuses_an_absent_display if {
	some msg in cp.deny with input as {"pages": [good]}
	startswith(msg, "D0:")
}

test_d1_refuses_an_unexplained_absence if {
	m := object.union(good_mount, {"params": [{"param": "bloom", "declared": "absent"}]})
	some msg in cp.deny with input as with_mount(m)
	startswith(msg, "D1:")
}

test_d2_refuses_a_reasonless_withhold if {
	m := object.union(good_mount, {"params": [{"param": "bloom", "declared": "withheld", "reason": "  "}]})
	some msg in cp.deny with input as with_mount(m)
	startswith(msg, "D2:")
}

test_d3_refuses_an_exposed_key_not_in_kcfg if {
	m := object.union(good_mount, {"params": [{"param": "bloom", "declared": "exposed", "spelling": "bloom", "in_kcfg": false, "on_page": true}]})
	some msg in cp.deny with input as with_mount(m)
	startswith(msg, "D3:")
}

test_d3_refuses_an_exposed_key_no_page_reaches if {
	m := object.union(good_mount, {"params": [{"param": "bloom", "declared": "exposed", "spelling": "bloom", "in_kcfg": true, "on_page": false}]})
	some msg in cp.deny with input as with_mount(m)
	startswith(msg, "D3:")
}

test_admits_every_page_and_param if {
	a := cp.admitted with input as {"pages": [good], "display": good_display}
	a == {"clock-config.qml", "clock/bloom", "clock/fill"}
}

# N1 (C2 `not k.value`): a null value was DENIED as undeclared
test_null_value_is_withheld_not_denied if {
	i := {"pages": [object.union(good, {"keys": [{"key": "bloom", "type": "Double", "value": null, "default": true}]})], "display": good_display}
	"C5: clock-config.qml: [\"cfg_bloom.value\"] was not measured" in cp.withheld with input as i
	d := cp.deny with input as i
	every m in d { not startswith(m, "C2:") }
	not "clock-config.qml" in cp.admitted with input as i
}

# N1 (C3 `not k.default`)
test_null_default_is_withheld_not_denied if {
	i := {"pages": [object.union(good, {"keys": [{"key": "bloom", "type": "Double", "value": true, "default": null}]})], "display": good_display}
	"C5: clock-config.qml: [\"cfg_bloom.default\"] was not measured" in cp.withheld with input as i
	d := cp.deny with input as i
	every m in d { not startswith(m, "C3:") }
}

# N1 (C4 `not p.withheld`): a null withheld dropped the page from C4
test_null_withheld_page_still_judged if {
	i := {"pages": [{"page": "e.qml", "withheld": null, "entries": 0, "declared": [], "keys": []}], "display": good_display}
	"C4: e.qml: its kcfg has no entries" in cp.deny with input as i
}

# N1 (D3 `not r.in_kcfg` / `not r.on_page`): a null was DENIED as not carried
test_null_in_kcfg_is_withheld_not_denied if {
	m := object.union(good_mount, {"params": [{"param": "bloom", "declared": "exposed", "spelling": "bloom", "in_kcfg": null, "on_page": true}]})
	"D5: clock/bloom: [\"in_kcfg\"] was not measured" in cp.withheld with input as with_mount(m)
	d := cp.deny with input as with_mount(m)
	every x in d { not startswith(x, "D3:") }
	not "clock/bloom" in cp.admitted with input as with_mount(m)
}

test_null_on_page_is_withheld_not_denied if {
	m := object.union(good_mount, {"params": [{"param": "bloom", "declared": "exposed", "spelling": "bloom", "in_kcfg": true, "on_page": null}]})
	"D5: clock/bloom: [\"on_page\"] was not measured" in cp.withheld with input as with_mount(m)
	d := cp.deny with input as with_mount(m)
	every x in d { not startswith(x, "D3:") }
}

# a null reason on a withheld param is no reason (trim_space(null) was undefined)
test_null_reason_is_denied if {
	m := object.union(good_mount, {"params": [{"param": "fill", "declared": "withheld", "reason": null}]})
	"D2: clock withholds fill with no reason" in cp.deny with input as with_mount(m)
}

test_all_null_case_withheld_only if {
	pg := {"page": "n.qml", "withheld": null, "entries": null, "declared": null, "keys": [{"key": "k", "type": null, "value": null, "default": null}]}
	mt := {"mount": "m", "has_page": null, "stray": [], "params": [{"param": "p", "declared": null, "in_kcfg": null, "on_page": null}]}
	i := {"pages": [pg], "display": {"params": ["p"], "mounts": [mt]}}
	w := cp.withheld with input as i
	some a in w
	startswith(a, "C5: n.qml:")
	"D5: m/p: [\"declared\"] was not measured" in w
	count(cp.admitted) == 0 with input as i
	count(cp.deny) == 0 with input as i
}

test_d4_refuses_a_stray_display_key if {
	m := object.union(good_mount, {"stray": ["dotFill"]})
	some msg in cp.deny with input as with_mount(m)
	startswith(msg, "D4:")
}
