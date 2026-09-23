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

# exactly-once: a case whose judged fields are all null is withheld, never judged
test_all_null_case_withheld_only if {
	inp := with_case({"path": "notes.md", "lines": null})
	w := k.withheld with input as inp
	"K3: notes.md: lines was not measured" in w
	d := k.deny with input as inp
	count([m | some m in d; contains(m, "notes.md")]) == 0
	not "notes.md" in k.admitted with input as inp
}

# N1 (K2 `not l.attribution`): a null attribution is neither attribution nor an
# offence — withheld
test_null_attribution_is_withheld if {
	inp := with_case({"path": "notes.md", "lines": [{"line": 2, "count": 2, "attribution": null}]})
	w := k.withheld with input as inp
	"K3: notes.md: lines[0].attribution was not measured" in w
	not "notes.md" in k.admitted with input as inp
	count(k.deny) == 0 with input as inp
}

test_k1_the_exclusion_is_by_path_only if {
	moved := {"path": "scripts/check_mark_copy.py", "lines": [self_line]}
	some msg in k.deny with input as with_case(moved)
	startswith(msg, "K2:")
}
