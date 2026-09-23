# METADATA
# title: "E0 — no emitter was run"
# description: |
#   The measurement is `scripts/check_emitters_run.py --json`: every emitter in
#   emitters.ORDER (and each EXTERNAL one whose input is present) run inside a
#   private copy of the tracked tree, the tracked files compared, and the real
#   tree fingerprinted before and after. An empty population is a broken run.
package el.emitters_run

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "E0: no emitter was run"
}

# METADATA
# title: "E1 — every emitter runs"
deny contains msg if {
	some c in object.get(input, "cases", [])
	c.rc != 0
	msg := sprintf("E1: %s did not run: %v", [c.module, c.detail])
}

# METADATA
# title: "E2 — what the emitters produce IS what is tracked"
# description: |
#   Regenerate-and-compare: a tracked file the run changed is drift between the
#   generator and the committed output.
deny contains msg if {
	some d in object.get(input, "drift", [])
	msg := sprintf("E2: %s drifted from its emitter:\n%s", [d.path, d.summary])
}

# METADATA
# title: "E3 — the check does not write the tree it checks"
# description: |
#   W68: the gate's other checks read the tracked outputs while this runs. Any
#   change to a tracked file's inode, mtime or size during the run is a deny.
deny contains msg if {
	some p in object.get(input, "tree_touched", [])
	msg := sprintf("E3: the run wrote the real tree: %s", [p])
}

withheld contains msg if {
	some w in object.get(input, "withheld", [])
	msg := sprintf("E0: %s skipped: %s", [w.module, w.withheld])
}

admitted contains c.module if {
	some c in object.get(input, "cases", [])
	c.rc == 0
}
