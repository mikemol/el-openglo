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

import data.el.truth

# ⚑ AN ABSENT POPULATION IS AN EMPTY ONE. `count(input.cases)` is UNDEFINED on {}
# and an undefined body ADMITS — a policy that certifies a measurement that never
# ran. object.get makes the empty case reachable, so it can deny.
deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "no actions measured: the population is empty, so nothing was judged"
}

# ⚑ PER OUTPUT, THE FACT IS JUDGED — NOT THE SUMMARY (W61). An action keyed one
# output at a time names each output whose key moved; each is a denial of its own,
# so the message says WHICH picture is stale, and a measurement whose summary
# `state` disagrees with its own stale list is still refused.
deny contains msg if {
	some c in input.cases
	some f in object.get(c, "stale_outputs", [])
	msg := sprintf(
		"action %q output %q is STALE: its inputs moved since it was built — rebuild it (render_screens renders only the stale)",
		[c.action, f],
	)
}

deny contains msg if {
	some c in input.cases
	c.state == "stale"
	count(object.get(c, "stale_outputs", [])) == 0
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
# ⚑ ∂ AT THE OUTPUT BOUNDARY. An action that writes a file it never declared is
# an action whose outputs cannot be split into per-artifact cones, so nobody can
# attribute that file's staleness to anything. Measured 2026-09-22: render_screens
# declared 36 outputs and wrote 55 — the 12 animations, 7 contact sheets and a
# README were produced and declared nowhere.
#
# ⚑ DENY, NOT WITHHELD, AND THE DIFFERENCE IS WHO CAN FIX IT. An unresolved edge
# is a limit of the SCANNER; an undeclared output is a defect in the ACTION's own
# declaration, which the action's author can close by naming the file.
deny contains msg if {
	some c in input.cases
	count(c.undeclared_outputs) > 0
	msg := sprintf("action %q writes %d file(s) it does not declare (%s): an undeclared output has no cone, so its staleness is unattributable", [c.action, count(c.undeclared_outputs), concat(", ", c.undeclared_outputs)])
}

# ⚑ AND THE OTHER ORIENTATION IS THE ORIGINAL INCIDENT, SEEN FROM THE FAR SIDE: a
# declared output that is not on disk is a build that did not finish. The commit
# that captured a pre-fix rendering was this, one frame earlier.
deny contains msg if {
	some c in input.cases
	count(c.declared_absent) > 0
	msg := sprintf("action %q declares %d output(s) that are ABSENT (%s): the build did not finish, or the plan names a file it never writes", [c.action, count(c.declared_absent), concat(", ", c.declared_absent)])
}

# ⚑ A KEY OVER AN UNDER-COVERED DOMAIN IS NOT EVIDENCE OF CURRENCY, and this rule
# exists because the tool shipped at b98f8cc without it: key_of returned a clean
# triple while its scanner had silently dropped every computed read. The caller
# read absence-of-error as coverage — "the trap for a closure tool is not 'the
# closure is wrong'; it is 'the closure dropped an unresolvable import and
# returned success'" (linux-sources-9c, 2026-09-22).
#
# ⚑ WITHHELD, NOT DENY, AND THE ASYMMETRY IS DELIBERATE. Over-approximating the
# DEPENDENCY set has no terminating condition; over-approximating the RESIDUE set
# does — a false positive costs one file declared uncovered, a false negative
# costs a wrong verdict. So this fires generously and never blocks.
withheld contains msg if {
	some c in input.cases
	c.n_unresolved > 0
	msg := sprintf("action %q keyed over a domain with %d UNRESOLVED edge(s): the key is evidence about what the scan COULD see", [c.action, c.n_unresolved])
}

withheld contains msg if {
	some c in input.cases
	c.n_undeclared_domains > 0
	msg := sprintf("action %q keyed over %d UNDECLARED domain(s) (glob/walk/listdir): the population itself is unknown, so neither boundary is computable over it", [c.action, c.n_undeclared_domains])
}

# ⚑ REFORMULATED IS NOT STALE. The key's DEFINITION changed, so the recorded key
# answers a different question; the artifacts may be perfectly current. Saying
# "STALE — rebuild" here is a false accusation the reader cannot check.
withheld contains msg if {
	some c in input.cases
	c.state == "reformulated"
	msg := sprintf("action %q was keyed under an older formula: re-record with scripts/check_action_key.py --write (this is NOT evidence the artifacts are stale)", [c.action])
}

withheld contains msg if {
	some c in input.cases
	c.state == "unrecorded"
	count(object.get(c, "unrecorded_outputs", [])) == 0
	msg := sprintf("action %q has no recorded key: currency is UNMEASURED, not confirmed", [c.action])
}

# an output never recorded is unmeasured, not stale — named, so the hole is visible
withheld contains msg if {
	some c in input.cases
	n := count(object.get(c, "unrecorded_outputs", []))
	n > 0
	msg := sprintf("action %q: %d of %d output(s) have no recorded key (%s): their currency is UNMEASURED", [c.action, n, object.get(c, "n_keyed_outputs", 0), concat(", ", c.unrecorded_outputs)])
}

withheld contains msg if {
	some c in input.cases
	c.state == "unmeasurable"
	msg := sprintf(
		"action %q declares host input(s) absent here (%s): the key is uncomputable on this machine",
		[c.action, concat(", ", c.missing_host)],
	)
}

# ⚑ AN UNPINNED HOST IS A WITHHELD FACT, NOT A FAILURE. It says the verdict holds
# on the machine that produced it and nowhere else. The operator's ruling —
# "you don't need a host binary, you need to define your host" — makes the fix a
# BUILT ARTIFACT (oci/Containerfile, pinned by digest in catalog/host.json), not
# a longer list of files. Enumerating host files declares edges where the thing
# needing declaration is a domain.
withheld contains msg if {
	object.get(input, ["host", "kind"], "") == "unpinned"
	some c in input.cases
	truth.py(c.sees_host)
	msg := sprintf(
		"action %q sees the host and the host is UNPINNED: staleness is detectable here, but a cached verdict is not transportable",
		[c.action],
	)
}

deny contains msg if {
	object.get(input, ["host", "kind"], "") == "unmeasurable"
	msg := sprintf("the host identity could not be computed: %s", [input.host.detail])
}

admitted contains msg if {
	some c in input.cases
	c.state == "current"
	count(object.get(c, "stale_outputs", [])) == 0
	msg := sprintf("action %q current: %d declared input(s) -> %d artifact(s)", [c.action, c.n_inputs, c.n_outputs])
}
