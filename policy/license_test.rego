package el.license_test

import data.el.license as lc
import rego.v1

cases := [
	{"kind": "authority", "where": "emitters.LICENSE_SPDX", "id": "Apache-2.0", "via": "constant"},
	{"kind": "generator", "where": "make_clock.py:63", "id": "Apache-2.0", "via": "LICENSE_SPDX"},
	{"kind": "file", "where": "LICENSE", "id": "Apache-2.0", "via": "text"},
]

good := {"cases": cases}

test_admits_an_apache_tree if {
	count(lc.deny) == 0 with input as good
}

test_l0_refuses_an_absent_population if {
	some msg in lc.deny with input as {}
	msg == "L0: no licence declaration was measured"
}

test_l0_refuses_an_empty_population if {
	some msg in lc.deny with input as {"cases": []}
	msg == "L0: no licence declaration was measured"
}

test_l0_refuses_a_missing_kind if {
	some msg in lc.deny with input as {"cases": [c | some c in cases; c.kind != "file"]}
	msg == "L0: no file declaration was measured"
}

test_l1_refuses_a_gpl_generator if {
	bad := {"kind": "generator", "where": "make_sddm.py:82", "id": "GPLv3", "via": "LICENSE_SPDX"}
	some msg in lc.deny with input as {"cases": array.concat(cases, [bad])}
	startswith(msg, "L1: make_sddm.py:82 declares")
	contains(msg, "GPLv3")
}

test_l1_refuses_a_gpl_licence_file if {
	bad := {"kind": "file", "where": "LICENSE", "id": "GPL-3.0", "via": "text"}
	some msg in lc.deny with input as {"cases": array.concat(cases, [bad])}
	startswith(msg, "L1: LICENSE declares")
}

test_l1_refuses_an_unresolved_declaration if {
	bad := {"kind": "file", "where": "pyproject.toml [project].license", "id": null, "via": "toml"}
	some msg in lc.deny with input as {"cases": array.concat(cases, [bad])}
	msg == "L1: pyproject.toml [project].license declares null, not Apache-2.0"
}

test_l2_refuses_a_literal_even_when_correct if {
	lit := {"kind": "generator", "where": "make_plasma.py:75", "id": "Apache-2.0", "via": "literal"}
	some msg in lc.deny with input as {"cases": array.concat(cases, [lit])}
	startswith(msg, "L2: make_plasma.py:75")
}

test_l2_admits_a_literal_outside_the_generators if {
	count(lc.deny) == 0 with input as {"cases": array.concat(cases, [{"kind": "file", "where": "x", "id": "Apache-2.0", "via": "toml"}])}
}
