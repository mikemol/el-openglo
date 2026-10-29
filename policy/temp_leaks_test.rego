package el.temp_leaks_test

import rego.v1

import data.el.temp_leaks

clean := {"subject": "import make_deb", "leaked": []}

leaky := {"subject": "check_cursors.measure", "leaked": ["el-cursors-abc12345"]}

test_absent_population_denied if {
	"T0: no subject's temp leftovers were measured" in temp_leaks.deny with input as {}
}

test_clean_admitted if {
	count(temp_leaks.deny) == 0 with input as {"cases": [clean]}
	temp_leaks.admitted == {"import make_deb"} with input as {"cases": [clean]}
}

test_leak_denied if {
	some m in temp_leaks.deny with input as {"cases": [clean, leaky]}
	startswith(m, "T1: check_cursors.measure left 1 temp entr(ies)")
}

test_leaky_is_not_admitted if {
	temp_leaks.admitted == {"import make_deb"} with input as {"cases": [clean, leaky]}
}

cache_ok := {"subject": "staging_cache.shared_stage", "leaked": [], "persistent": {"el-openglo-stage": [".lock", "stage-aaaa", "stage-bbbb"]}}

test_bounded_cache_admitted if {
	count(temp_leaks.deny) == 0 with input as {"cases": [cache_ok], "cache_keep": 2}
}

test_unbounded_cache_denied if {
	big := object.union(cache_ok, {"persistent": {"el-openglo-stage": [".lock", "stage-a", "stage-b", "stage-c"]}})
	some m in temp_leaks.deny with input as {"cases": [big], "cache_keep": 2}
	startswith(m, "T2: staging_cache.shared_stage kept 3 trees")
}

test_partial_staging_denied if {
	dead := object.union(cache_ok, {"persistent": {"el-openglo-stage": [".lock", "stage-a", ".part-xyz"]}})
	some m in temp_leaks.deny with input as {"cases": [dead], "cache_keep": 2}
	startswith(m, "T2: staging_cache.shared_stage left a partial staging .part-xyz")
}

test_deferred_is_withheld_not_denied if {
	i := {"cases": [clean], "withheld": ["check_urgency_cues.measure: deferred"]}
	count(temp_leaks.deny) == 0 with input as i
	count(temp_leaks.withheld) == 1 with input as i
}
