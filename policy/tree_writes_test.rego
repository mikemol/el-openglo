package el.tree_writes_test

import rego.v1

import data.el.tree_writes

clean := {"key": "A", "check": "tool:a.py", "rc": 0, "written": []}

writer := {"key": "B", "check": "tool:b.py", "rc": 0, "written": ["plasma-clock/x.json"]}

test_absent_population_denied if {
	"T0: no claim's check was measured" in tree_writes.deny with input as {}
}

test_writer_denied if {
	some m in tree_writes.deny with input as {"cases": [clean, writer]}
	startswith(m, "T1: @B (tool:b.py) wrote 1 tracked file(s)")
}

test_failing_check_that_writes_is_still_denied if {
	count(tree_writes.deny) == 1 with input as {"cases": [object.union(writer, {"rc": 1})]}
}

test_withheld_writer_denied if {
	some m in tree_writes.deny with input as {"cases": [clean], "withheld": [object.union(writer, {"withheld": "exceeded 900 s"})]}
	startswith(m, "T1: @B")
}

test_clean_admitted if {
	count(tree_writes.deny) == 0 with input as {"cases": [clean]}
	tree_writes.admitted == {"A"} with input as {"cases": [clean]}
}

test_unobserved_is_withheld_not_admitted if {
	count(tree_writes.withheld) == 1 with input as {"cases": [clean], "withheld": [{"key": "C", "check": "x:y", "withheld": "command not found (127)"}]}
	tree_writes.admitted == {"A"} with input as {"cases": [clean], "withheld": [{"key": "C", "check": "x:y", "withheld": "command not found (127)"}]}
}
