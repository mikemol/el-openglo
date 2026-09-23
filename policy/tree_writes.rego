# METADATA
# title: "T0 — no claim's check was measured"
# description: |
#   The measurement is `scripts/check_tree_writes.py --json`: each worklist
#   claim's check run serially in a scratch worktree, every tracked file
#   fingerprinted (inode, mtime_ns, size) before and after. An empty population
#   is a broken run, not a clean tree.
package el.tree_writes

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "T0: no claim's check was measured"
}

# METADATA
# title: "T1 — no gated check writes a tracked file (W68)"
# description: |
#   A check that writes the tree mutates the inputs of every check running
#   beside it in the gate; that is the race @EMITTERS' E3 saw.
deny contains msg if {
	some c in array.concat(object.get(input, "cases", []), object.get(input, "withheld", []))
	count(object.get(c, "written", [])) > 0
	msg := sprintf("T1: @%s (%s) wrote %d tracked file(s): %v", [c.key, c.check, count(c.written), c.written])
}

withheld contains msg if {
	some w in object.get(input, "withheld", [])
	msg := sprintf("T0: @%s not observed: %s", [w.key, w.withheld])
}

admitted contains c.key if {
	some c in object.get(input, "cases", [])
	count(object.get(c, "written", [])) == 0
}
