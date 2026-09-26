package el.deb_test

import data.el.deb
import rego.v1

steps_ok := {"clamp": 0, "build": 0, "info": 0, "contents": 0}

good := {"steps": steps_ok, "staged": ["/usr/a", "/usr/b"], "packed": ["/usr/a", "/usr/b"],
	"verdict": {"state": "ok", "sha256": "ab"}, "withheld": []}

test_complete_pack_admits if {
	d := deb.deny with input as good
	count(d) == 0
}

test_empty_population_denied if {
	d := deb.deny with input as {}
	"D0: no staged file measured: the search is broken" in d
}

test_failed_step_denied if {
	d := deb.deny with input as object.union(good, {"steps": object.union(steps_ok, {"build": 2})})
	some m in d
	startswith(m, "D1:")
}

test_step_never_ran_denied if {
	# built whole: object.union merges nested objects, so it would keep the other steps
	i := {"steps": {"clamp": 0}, "staged": good.staged, "packed": good.packed, "withheld": []}
	d := deb.deny with input as i
	some m in d
	contains(m, "null = never ran")
}

test_missing_file_denied if {
	d := deb.deny with input as object.union(good, {"packed": ["/usr/a"]})
	"D2: /usr/b was staged but is not in the package" in d
}

test_foreign_file_denied if {
	d := deb.deny with input as object.union(good, {"packed": ["/usr/a", "/usr/b", "/usr/c"]})
	some m in d
	startswith(m, "D3:")
}

test_refused_verdict_denied if {
	d := deb.deny with input as object.union(good, {"verdict": {"state": "refused", "step": "build"}})
	some m in d
	startswith(m, "D4:")
}

test_withheld_is_not_denied if {
	i := {"withheld": ["no deb_pack output"]}
	d := deb.deny with input as i
	w := deb.withheld with input as i
	count(d) == 0
	count(w) == 1
}
