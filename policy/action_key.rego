# A committed artifact must be CURRENT: built from the inputs that are in the tree
# now, not from inputs that have since changed.
#
# ⚑ THE INCIDENT (2026-09-22). The operator reported grid glitching in a checked-in
# screen. It was fixed and the fix was proven — and the commit captured the PRE-FIX
# picture, because the 48-render sweep had not finished. The operator: "now the
# visual artifact I noticed is fixed. The fact that the updated images didn't go
# with the commit hasn't been fixed." A defect already pointed at twice recurred
# because a verdict was read off a stale artifact.
#
# ⚑ CURRENCY IS NOT A BOUNDARY. build_graph asks PRODUCED and CONSUMED; a file can
# be both and still be wrong. This is the third obligation.
package el.action_key

# ⚑ AN ABSENT POPULATION IS AN EMPTY ONE. `count(input.cases)` is UNDEFINED on {}
# and an undefined body ADMITS — a policy that certifies a measurement that never
# ran. object.get makes the empty case reachable, so it can deny.
deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "no actions measured: the population is empty, so nothing was judged"
}

deny contains msg if {
	some c in input.cases
	c.state == "stale"
	msg := sprintf(
		"action %q is STALE: outputs were built at key %s but its declared inputs now key %s — rebuild, then scripts/check_action_key.py --write",
		[c.action, substring(c.recorded_key, 0, 16), substring(c.key, 0, 16)],
	)
}

# ⚑ AN ACTION THAT CLAIMS NO OUTPUTS IS NOT A PASSING ACTION, it is a broken
# search. "0 stale over 0 artifacts" and "0 stale over 55 artifacts" must not
# read the same — the repo's n-of-m rule, as a requirement rather than a print.
deny contains msg if {
	some c in input.cases
	c.n_outputs == 0
	msg := sprintf("action %q declares outputs but none were found: the output domain is broken, not clean", [c.action])
}

deny contains msg if {
	some c in input.cases
	c.n_inputs == 0
	msg := sprintf("action %q has an EMPTY input domain: its key is a constant and can never move", [c.action])
}

# ⚑ NOT CONFIRMED IS NOT FAILED. No recorded key means nobody asserted a build;
# an absent host input means the key cannot be computed on this machine. Both are
# facts about the record and the machine, not about the artifact.
withheld contains msg if {
	some c in input.cases
	c.state == "unrecorded"
	msg := sprintf("action %q has no recorded key: currency is UNMEASURED, not confirmed", [c.action])
}

withheld contains msg if {
	some c in input.cases
	c.state == "unmeasurable"
	msg := sprintf(
		"action %q declares host input(s) absent here (%s): the key is uncomputable on this machine",
		[c.action, concat(", ", c.missing_host)],
	)
}

admitted contains msg if {
	some c in input.cases
	c.state == "current"
	msg := sprintf("action %q current: %d declared input(s) -> %d artifact(s)", [c.action, c.n_inputs, c.n_outputs])
}
