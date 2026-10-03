package el.contracts_test

import data.el.contracts as p
import rego.v1

name := "render_screens.animation"

emits := [
	"file", "variant", "exists", "frames", "width", "axis", "pips", "floor", "shifts", "tears",
	"seamless", "fractional_share", "dominant_period", "dominant_line_share", "spectral_power",
	"period2_share", "logged_steps",
]

good := {"surfaces": [{"surface": name, "emitted": emits, "consumers": [
	{"file": "scripts/check_screens.py", "reads": [{"field": "shifts", "line": 55}, {"field": "exists", "line": 153}]},
]}]}

test_admits_a_kept_contract if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	name in p.admitted with input as good
}

test_k0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "K0:")
}

test_k0_refuses_an_empty_population if {
	some msg in p.deny with input as {"surfaces": []}
	startswith(msg, "K0:")
}

test_k1_refuses_an_undeclared_surface if {
	bad := {"surfaces": [{"surface": "make_x.row", "emitted": ["a"], "consumers": []}]}
	some msg in p.deny with input as bad
	startswith(msg, "K1:")
}

test_k2_refuses_a_read_of_an_undeclared_field if {
	bad := object.union(good, {"surfaces": [{"surface": name, "emitted": emits, "consumers": [
		{"file": "scripts/check_screens.py", "reads": [{"field": "variants", "line": 9}]},
	]}]})
	some msg in p.deny with input as bad
	msg == "K2: scripts/check_screens.py:9 reads variants, which render_screens.animation does not declare"
	not name in p.admitted with input as bad
}

test_k3_refuses_a_declared_field_not_emitted if {
	bad := {"surfaces": [{"surface": name, "emitted": ["file", "variant", "exists"], "consumers": []}]}
	some msg in p.deny with input as bad
	startswith(msg, "K3:")
	contains(msg, "tears")
}

test_unreadable_producer_is_withheld_not_judged if {
	inp := {"surfaces": [{"surface": name, "emitted": null, "consumers": [{"file": "c.py", "reads": []}]}]}
	count(p.deny) == 0 with input as inp
	"render_screens.animation: the producer was not readable" in p.withheld with input as inp
	count(p.admitted) == 0 with input as inp
}

test_unreadable_consumer_is_withheld_not_judged if {
	inp := {"surfaces": [{"surface": name, "emitted": emits, "consumers": [{"file": "c.py", "reads": null}]}]}
	count(p.deny) == 0 with input as inp
	"render_screens.animation: consumer c.py was not readable" in p.withheld with input as inp
	count(p.admitted) == 0 with input as inp
}
