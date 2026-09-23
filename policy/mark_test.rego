package el.mark_test

import data.el.mark as k
import rego.v1

self_line := {"line": 32, "count": 1, "attribution": false}

clean := {"mark": "m", "source": "git", "cases": [
	{"path": "README.md", "lines": []},
	{"path": "scripts/check_mark.py", "lines": [self_line]},
	{"path": "catalog/design.md", "lines": [{"line": 4, "count": 1, "attribution": true}]},
]}

with_case(c) := object.union(clean, {"cases": array.concat(clean.cases, [c])})

test_admits_a_scrubbed_tree if {
	count(k.deny) == 0 with input as clean
	count(k.admitted) == 3 with input as clean
}

test_k0_refuses_an_absent_population if {
	some msg in k.deny with input as {}
	startswith(msg, "K0:")
}

test_k0_refuses_an_empty_scan if {
	some msg in k.deny with input as {"cases": []}
	startswith(msg, "K0:")
}

# the failure the old selftest planted: a project calling ITSELF by the mark
test_k2_refuses_self_naming if {
	bad := {"path": "selfname.md", "lines": [{"line": 1, "count": 1, "attribution": false}]}
	some msg in k.deny with input as with_case(bad)
	msg == "K2: the retired mark appears 1× in selfname.md"
	k.offending == {"selfname.md": 1} with input as with_case(bad)
}

# one allowed attribution line must not excuse its neighbours
test_k2_an_attribution_line_does_not_excuse_its_neighbour if {
	mixed := {"path": "notes.md", "lines": [
		{"line": 1, "count": 1, "attribution": true},
		{"line": 2, "count": 2, "attribution": false},
	]}
	some msg in k.deny with input as with_case(mixed)
	msg == "K2: the retired mark appears 2× in notes.md"
}

test_k1_the_exclusion_is_by_path_only if {
	moved := {"path": "scripts/check_mark_copy.py", "lines": [self_line]}
	some msg in k.deny with input as with_case(moved)
	startswith(msg, "K2:")
}
