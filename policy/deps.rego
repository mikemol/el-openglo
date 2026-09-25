# METADATA
# title: "D0 — a manifest exists and the import walk found something"
# description: |
#   The measurement is `scripts/check_deps.py --json`: whether pyproject.toml
#   exists, and per third-party import found by the AST walk (every tracked module
#   in SCAN_DIRS, function bodies included): its distribution name, the files that
#   import it, whether that distribution is DECLARED (dependencies or an extra),
#   and whether the name is RECORDED in the manifest's text (the "deliberately
#   absent" notes). Weakness: `recorded` is a mention, so a name that merely
#   appears in a comment is recorded; the policy says which admissions rest on it.
package el.deps

import rego.v1

deny contains "D0: the import walk found nothing; the walk is broken, not the tree dependency-free" if {
	count(object.get(input, "cases", [])) == 0
}

deny contains "D0: no pyproject.toml to account against" if {
	input.manifest == false
}

# METADATA
# title: "D1 — every third-party import is declared, or recorded as deliberately absent"
deny contains msg if {
	some c in input.cases
	c.declared == false
	c.recorded == false
	msg := sprintf("D1: %s is neither declared nor recorded as absent (imported by %s)", [c.id, concat(", ", c.files)])
}

unmeasured(c) := {k |
	some k in ["declared", "recorded"]
	not is_boolean(object.get(c, k, null))
}

withheld contains msg if {
	some c in input.cases
	some k in unmeasured(c)
	msg := sprintf("W: %s: %s was not measured", [c.id, k])
}

withheld contains "W: manifest was not measured" if {
	not is_boolean(object.get(input, "manifest", null))
}

admitted contains c.id if {
	some c in input.cases
	count(unmeasured(c)) == 0
	accounted(c)
}

accounted(c) if c.declared == true

accounted(c) if c.recorded == true
