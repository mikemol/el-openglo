# METADATA
# title: "P0 — no scenario measured admits nothing"
# description: |
#   The measurement is `scripts/check_post_commit.py --json`: the repo's REAL
#   .githooks/post-commit run in a scratch repository with one file staged beside
#   the file the commit names. W561: a plain `git commit --amend` in that hook folds
#   the whole index into the tip, so a file staged during a gate landed in a stack's
#   last commit.
# custom:
#   family: gate
package el.post_commit

import rego.v1

# a hook that is not there is a fact about the checkout, not a clean hook
deny contains "P0: no post-commit scenario was measured; the search is broken, not the hook sound" if {
	count(object.get(input, "cases", [])) == 0
	object.get(input, "hook_present", null) != false
}

withheld contains "P3: .githooks/post-commit is absent; the amend was not exercised" if {
	object.get(input, "hook_present", null) == false
}

# METADATA
# title: "P1 — the amend leaves the staged file out of the tip"
deny contains msg if {
	some c in object.get(input, "cases", [])
	c.folded == true
	msg := sprintf("P1: %s: the hook's amend committed the staged file into the tip", [c.scenario])
}

# METADATA
# title: "P2 — the amend leaves the staged file staged"
# description: |
#   A file staged for the next commit must still be staged afterwards; an amend that
#   takes it out of the index loses the caller's work as surely as one that commits it.
deny contains msg if {
	some c in object.get(input, "cases", [])
	c.still_staged == false
	msg := sprintf("P2: %s: the hook's amend removed the staged file from the index", [c.scenario])
}

# METADATA
# title: "P3 — a hook that did not amend exercised nothing, and a fact not stated is withheld"
# description: |
#   `amended`, `folded` and `still_staged` are booleans the measurement always
#   emits. Null or absent is "could not say": P1/P2 are silent about it and it is
#   withheld by name. A hook that never amended proves nothing about the amend.
withheld contains msg if {
	some c in object.get(input, "cases", [])
	some f in ["amended", "folded", "still_staged"]
	not is_boolean(object.get(c, f, null))
	msg := sprintf("P3: %s: %s was not measured", [object.get(c, "scenario", "?"), f])
}

withheld contains msg if {
	some c in object.get(input, "cases", [])
	c.amended == false
	msg := sprintf("P3: %s: the hook did not amend, so the leak was not exercised", [c.scenario])
}

admitted contains c.scenario if {
	some c in object.get(input, "cases", [])
	c.amended == true
	c.folded == false
	c.still_staged == true
}
