package el.populations_test

import rego.v1

import data.el.populations

bare := {"module": "scripts/x.py", "line": 4, "kind": "walk", "recursive": true, "reach": "root", "root": "ROOT", "marked": false, "reason": null, "borrowed": false}

unknown := {"module": "scripts/x.py", "line": 5, "kind": "walk", "recursive": true, "reach": "unknown", "root": "d", "marked": false, "reason": null, "borrowed": false}

bounded := {"module": "scripts/x.py", "line": 6, "kind": "walk", "recursive": true, "reach": "bounded", "root": "ROOT/catalog", "marked": false, "reason": null, "borrowed": false}

marked := {"module": "scripts/x.py", "line": 7, "kind": "walk", "recursive": true, "reach": "unknown", "root": "td", "marked": true, "reason": "a private tempdir", "borrowed": false}

marked_bare := {"module": "scripts/x.py", "line": 8, "kind": "walk", "recursive": true, "reach": "root", "root": "ROOT", "marked": true, "reason": "", "borrowed": false}

listing := {"module": "scripts/x.py", "line": 9, "kind": "listdir", "recursive": false, "reach": "root", "root": "ROOT", "marked": false, "reason": null, "borrowed": false}

borrowed := {"module": "scripts/ratchet.py", "line": 3, "kind": "walk", "recursive": true, "reach": "root", "root": "ROOT", "marked": false, "reason": null, "borrowed": true}

test_absent_population_denied if {
	"P0: no file was in the census scope" in populations.deny with input as {}
}

test_empty_population_denied if {
	"P0: no file was in the census scope" in populations.deny with input as {"files": [], "cases": []}
}

test_bare_root_walk_denied if {
	some m in populations.deny with input as {"files": ["scripts/x.py"], "cases": [bare]}
	startswith(m, "P1: scripts/x.py:4")
}

test_unknown_root_walk_denied if {
	some m in populations.deny with input as {"files": ["scripts/x.py"], "cases": [unknown]}
	startswith(m, "P1: scripts/x.py:5")
}

test_marked_without_reason_denied if {
	some m in populations.deny with input as {"files": ["scripts/x.py"], "cases": [marked_bare]}
	startswith(m, "P2: scripts/x.py:8")
}

test_borrowed_is_withheld_not_denied if {
	count(populations.deny) == 0 with input as {"files": ["scripts/ratchet.py"], "cases": [borrowed]}
	count(populations.withheld) == 1 with input as {"files": ["scripts/ratchet.py"], "cases": [borrowed]}
}

test_bounded_marked_and_listing_admitted if {
	count(populations.deny) == 0 with input as {"files": ["scripts/x.py"], "cases": [bounded, marked, listing]}
}

test_no_sites_over_a_population_admitted if {
	count(populations.deny) == 0 with input as {"files": ["scripts/x.py"], "cases": []}
}
