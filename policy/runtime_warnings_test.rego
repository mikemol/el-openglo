package el.runtime_warnings_test

import data.el.runtime_warnings as r
import rego.v1

ruled := {"class": "a", "ruled": true, "rule_file": "policy/x.rego", "rule_file_exists": true, "unruled_since": null, "unruled_days": null}

fresh := {"class": "b", "ruled": false, "rule_file": null, "rule_file_exists": null, "unruled_since": "2026-09-30", "unruled_days": 1}

good := {"cases": [ruled, fresh], "withheld": null, "max_unruled_days": 7}

test_admits_ruled_and_fresh_unruled if {
	count(r.deny) == 0 with input as good
}

test_r0_refuses_an_absent_corpus if {
	"R0: no runtime-warning class was measured" in r.deny with input as {}
}

test_r1_refuses_an_unruled_row_without_a_date if {
	bad := object.union(fresh, {"unruled_since": null, "unruled_days": null})
	"R1: b has no rule and no unruled_since date" in r.deny with input as object.union(good, {"cases": [bad]})
}

test_r2_refuses_a_stale_unruled_row if {
	bad := object.union(fresh, {"unruled_days": 9})
	"R2: b unruled for 9 days (limit 7)" in r.deny with input as object.union(good, {"cases": [bad]})
}

test_r3_refuses_a_missing_rule_file if {
	bad := object.union(ruled, {"rule_file_exists": false})
	"R3: a cites policy/x.rego, which does not exist" in r.deny with input as object.union(good, {"cases": [bad]})
}

test_r4_withholds_an_unread_corpus if {
	some m in r.withheld with input as {"cases": [], "withheld": "OSError: x"}
	startswith(m, "R4:")
	count(r.deny) == 0 with input as {"cases": [], "withheld": "OSError: x"}
}
