# METADATA
# title: "H0 — no hooks measured admits nothing"
# description: |
#   The measurement is `scripts/check_hooks.py --json`: for each borrowed hook
#   (symlinked from substrate), whether it resolves here, where, and its
#   `--selftest` exit code and last output line when run FROM THIS REPO — a
#   symlinked script reads this repo's files while its code lives elsewhere.
package el.hooks

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "H0: no hooks were measured; the roster is empty, not the hooks healthy"
}

# METADATA
# title: "H1 — a missing hook is a FAILURE, not a skip"
# description: |
#   A dangling symlink or a moved upstream file is red: a check that quietly
#   passes when its subject is absent measures nothing.
deny contains msg if {
	some c in input.cases
	not c.present
	msg := sprintf("H1: %s: absent (dangling symlink, or not installed yet)", [c.hook])
}

# METADATA
# title: "H2 — every hook's selftest passes from this repo"
deny contains msg if {
	some c in input.cases
	c.present
	c.rc != 0
	msg := sprintf("H2: %s: selftest exited %d: %s", [c.hook, c.rc, c.tail])
}

admitted contains c.hook if {
	some c in input.cases
	c.present
	c.rc == 0
}
