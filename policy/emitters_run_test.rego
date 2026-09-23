package el.emitters_run_test

import rego.v1

import data.el.emitters_run

ran := {"module": "make_x", "rc": 0, "detail": "ok"}

broke := {"module": "make_y", "rc": 1, "detail": "NameError"}

test_absent_population_denied if {
	"E0: no emitter was run" in emitters_run.deny with input as {}
}

test_failed_emitter_denied if {
	"E1: make_y did not run: NameError" in emitters_run.deny with input as {"cases": [ran, broke]}
}

test_drift_denied if {
	some m in emitters_run.deny with input as {"cases": [ran], "drift": [{"path": "EL-X.colors", "summary": "+A=2"}]}
	startswith(m, "E2: EL-X.colors drifted")
}

test_tree_write_denied if {
	"E3: the run wrote the real tree: EL-X.colors" in emitters_run.deny with input as {"cases": [ran], "tree_touched": ["EL-X.colors"]}
}

test_clean_run_admitted if {
	count(emitters_run.deny) == 0 with input as {"cases": [ran], "drift": [], "tree_touched": []}
	emitters_run.admitted == {"make_x"} with input as {"cases": [ran], "drift": [], "tree_touched": []}
}

test_skip_is_withheld_not_denied if {
	count(emitters_run.deny) == 0 with input as {"cases": [ran], "withheld": [{"module": "make_k", "withheld": "needs /tmp/K"}]}
	count(emitters_run.withheld) == 1 with input as {"cases": [ran], "withheld": [{"module": "make_k", "withheld": "needs /tmp/K"}]}
}
