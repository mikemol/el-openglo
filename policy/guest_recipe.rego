# METADATA
# title: "R0 — no recipe measured admits nothing"
# description: |
#   The measurement is `scripts/guest_recipe.py --json`: the guest image recipe's
#   snapshot pin, whether its mirror resolves through snapshot.debian.org at that pin,
#   its suite, the decided packages it lacks and the absent set it lets in. W235;
#   catalog/guest-image.md (a)-(e).
package el.guest_recipe

import rego.v1

deny contains "R0: no recipe was measured" if {
	count(object.get(input, "cases", [])) == 0
	count(object.get(input, "withheld", [])) == 0
}

# METADATA
# title: "R1 — the snapshot is a pinned timestamp (an unpinned build is not reproducible)"
deny contains msg if {
	some c in input.cases
	c.snapshot_pinned == false
	msg := sprintf("R1: %s: snapshot %v is not a pinned YYYYMMDDTHHMMSSZ timestamp", [c.recipe, c.snapshot])
}

# METADATA
# title: "R2 — the mirror resolves through snapshot.debian.org at the pin"
deny contains msg if {
	some c in input.cases
	c.mirror_through_snapshot == false
	msg := sprintf("R2: %s: the mirror is not snapshot.debian.org at {snapshot}", [c.recipe])
}

# METADATA
# title: "R3 — the suite is the decided base"
deny contains msg if {
	some c in input.cases
	c.suite != c.want_suite
	msg := sprintf("R3: %s: suite %v, decided %v", [c.recipe, c.suite, c.want_suite])
}

# METADATA
# title: "R4 — the decided packages are in, the absent set is out"
deny contains msg if {
	some c in input.cases
	some p in c.missing
	msg := sprintf("R4: %s: decided package %s is not in the set", [c.recipe, p])
}

deny contains msg if {
	some c in input.cases
	some p in c.forbidden_present
	msg := sprintf("R4: %s: %s is declared absent but is in the set", [c.recipe, p])
}

withheld contains msg if {
	some msg in object.get(input, "withheld", [])
}
