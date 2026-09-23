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
	c.present == false
	msg := sprintf("H1: %s: absent (dangling symlink, or not installed yet)", [c.hook])
}

# measured: a present hook whose selftest ran. The measurement always emits
# `present` (bool); `rc` is null ONLY for an absent hook (legitimately — there
# was nothing to run), so a present hook with a non-numeric rc could not say.
measured(c) if {
	c.present == true
	is_number(c.rc)
}

# METADATA
# title: "H3 — a hook the measurement could not describe is withheld, not judged"
withheld contains msg if {
	some c in input.cases
	not is_boolean(object.get(c, "present", null))
	msg := sprintf("H3: %v: present was not measured", [object.get(c, "hook", null)])
}

withheld contains msg if {
	some c in input.cases
	c.present == true
	not measured(c)
	msg := sprintf("H3: %v: rc was not measured", [object.get(c, "hook", null)])
}

# METADATA
# title: "H2 — every hook's selftest passes from this repo"
deny contains msg if {
	some c in input.cases
	measured(c)
	c.rc != 0
	msg := sprintf("H2: %s: selftest exited %d: %s", [c.hook, c.rc, c.tail])
}

admitted contains c.hook if {
	some c in input.cases
	measured(c)
	c.rc == 0
}
