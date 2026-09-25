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

lsfiles := {"module": "scripts/check_license.py", "line": 195, "kind": "git-ls-files", "recursive": true, "reach": "root", "root": "git ls-files", "marked": false, "reason": null, "borrowed": false}

# R6: the bypass that graded @LICENSE broken in Δ's sandbox
test_raw_git_ls_files_denied_as_p3_not_p1 if {
	inp := {"files": ["scripts/check_license.py"], "cases": [lsfiles]}
	some m in populations.deny with input as inp
	startswith(m, "P3: scripts/check_license.py:195 runs `git ls-files` directly")
	count([n | some n in populations.deny with input as inp; startswith(n, "P1:")]) == 0
}

test_git_ls_files_in_the_authority_is_admitted if {
	own := object.union(lsfiles, {"module": "scripts/git_tracked.py"})
	count(populations.deny) == 0 with input as {"files": ["scripts/git_tracked.py"], "cases": [own]}
}

test_marked_git_ls_files_is_admitted if {
	m := object.union(lsfiles, {"marked": true, "reason": "untracked files of a real repo"})
	count(populations.deny) == 0 with input as {"files": ["scripts/check_license.py"], "cases": [m]}
}

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

# null is truthy to a bare Rego reference: a null recursive/marked must not fire P1/P2
test_null_recursive_marked_does_not_fire if {
	inp := {"files": ["scripts/x.py"], "cases": [
		object.union(bare, {"recursive": null}),
		object.union(marked_bare, {"marked": null, "recursive": false}),
	]}
	count(populations.deny) == 0 with input as inp
}

# a null borrowed/recursive must not produce a SUBSTRATE withheld finding — it is
# withheld as NOT MEASURED instead (was: count(withheld) == 0, which is the
# silently-nothing the exactly-once rule forbids)
test_null_borrowed_recursive_does_not_withhold if {
	inp := {"files": ["scripts/ratchet.py"], "cases": [
		object.union(borrowed, {"recursive": null}),
		object.union(bare, {"borrowed": null, "recursive": false, "line": 10}),
	]}
	w := populations.withheld with input as inp
	every m in w { not contains(m, "SUBSTRATE") }
	w == {"P1: scripts/ratchet.py:3: recursive was not measured", "P1: scripts/x.py:10: borrowed was not measured"}
}

test_all_null_case_withheld_only if {
	c := {"module": "scripts/x.py", "line": 4, "kind": "walk", "recursive": null, "reach": null, "root": "ROOT", "marked": null, "reason": null, "borrowed": null}
	inp := {"files": ["scripts/x.py"], "cases": [c]}
	count(populations.deny) == 0 with input as inp
	w := populations.withheld with input as inp
	w == {
		"P1: scripts/x.py:4: borrowed was not measured",
		"P1: scripts/x.py:4: recursive was not measured",
		"P1: scripts/x.py:4: marked was not measured",
		"P1: scripts/x.py:4: reach was not measured",
	}
}

# N1 fix (lines 32/41): HEAD's `not c.borrowed` read a null borrowed as borrowed:
# the unmarked root walk was neither denied nor withheld
test_null_borrowed_is_withheld if {
	inp := {"files": ["scripts/x.py"], "cases": [object.union(bare, {"borrowed": null})]}
	"P1: scripts/x.py:4: borrowed was not measured" in populations.withheld with input as inp
}

# N1 fix (lines 35/54): a null marked read as marked
test_null_marked_is_withheld if {
	inp := {"files": ["scripts/x.py"], "cases": [object.union(bare, {"marked": null})]}
	"P1: scripts/x.py:4: marked was not measured" in populations.withheld with input as inp
}

test_null_marked_borrowed_is_withheld_not_substrate if {
	inp := {"files": ["scripts/ratchet.py"], "cases": [object.union(borrowed, {"marked": null})]}
	populations.withheld == {"P1: scripts/ratchet.py:3: marked was not measured"} with input as inp
}

test_no_sites_over_a_population_admitted if {
	count(populations.deny) == 0 with input as {"files": ["scripts/x.py"], "cases": []}
}
