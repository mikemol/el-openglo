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

test_deferred_is_withheld_not_denied if {
	i := {"cases": [clean], "withheld": ["check_urgency_cues.measure: deferred"]}
	count(temp_leaks.deny) == 0 with input as i
	count(temp_leaks.withheld) == 1 with input as i
}
