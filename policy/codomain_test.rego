package el.codomain_test

import data.el.codomain as c
import rego.v1

em := [{"target": "konsole", "emitter": "make_konsole", "venues": ["KDE Store"]}]

gap := {"target": "vscode", "family": "editor", "contract": "VS Code theme JSON", "venue": "Marketplace", "licence": "Apache-2.0", "reach": 5, "cost": 3, "missing": [], "rank": 15}

good := {"emitted": em, "gaps": [gap], "gaps_withheld": null}

test_admits_a_complete_map if {
	count(c.deny) == 0 with input as good
	count(c.withheld) == 0 with input as good
}

test_c0_refuses_an_absent_population if {
	"C0: no emitted surface was measured; the roster read is broken" in c.deny with input as {}
}

test_c0_refuses_an_empty_emitted_half if {
	"C0: no emitted surface was measured; the roster read is broken" in c.deny with input as object.union(good, {"emitted": []})
}

test_c1_refuses_a_gap_without_a_contract if {
	bad := object.union(gap, {"contract": null, "missing": ["contract"]})
	"C1: gap vscode lacks [\"contract\"]" in c.deny with input as object.union(good, {"gaps": [bad]})
}

test_c2_refuses_a_gap_already_emitted if {
	bad := object.union(gap, {"target": "konsole"})
	"C2: gap konsole is already emitted (make_konsole)" in c.deny with input as object.union(good, {"gaps": [bad]})
}

test_c3_withholds_an_unread_gaps_file if {
	some m in c.withheld with input as object.union(good, {"gaps": [], "gaps_withheld": "OSError: x"})
	startswith(m, "C3:")
}
