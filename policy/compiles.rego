# METADATA
# title: "K0 — no sources measured admits nothing"
# description: |
#   The measurement is `scripts/check_compiles.py --json`: one case per TRACKED
#   .py outside scripts/ and catalog/ (git_tracked, never a disk walk), with
#   py_compile's error or null. Weakness, stated: compiling proves the syntax
#   survived the recovery and nothing about behaviour — eight partial files
#   compile (check_partial is the separate claim).
package el.compiles

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "K0: no sources were measured; the search is broken, not the tree clean"
}

# METADATA
# title: "K1 — every tracked source byte-compiles"
deny contains msg if {
	some c in input.cases
	c.error != null
	msg := sprintf("K1: %s: %s", [c.id, c.error])
}

admitted contains c.id if {
	some c in input.cases
	c.error == null
}
