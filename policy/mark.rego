# METADATA
# title: "K0 — an empty scan admits nothing"
# description: |
#   The measurement is `scripts/check_mark.py --json`: every file in the tree and,
#   per file, each line carrying the retired mark (its count, and whether the line
#   reads as attribution). The population is the TREE, not the hits: zero files
#   scanned is a broken search, not a scrubbed tree.
package el.mark

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "K0: no file was scanned for the retired mark"
}

# METADATA
# title: "K1 — paths excluded from the scrub, each for a stated reason"
excluded := {
	"scripts/check_mark.py": "this file must name the mark to look for it",
	"RECOVERY-NOTES.md": "verbatim provenance record of the pre-rename recovery",
}

# METADATA
# title: "K2 — the retired mark appears nowhere but attribution"
# description: |
#   Naming the product that INSPIRED the look ("the Timex ... era") is nominative
#   reference and is allowed, per LINE — one allowed line must not excuse its
#   neighbours. Every other occurrence outside `excluded` is a finding.
offending[c.path] := n if {
	some c in input.cases
	not excluded[c.path]
	n := sum([l.count | some l in c.lines; not l.attribution])
	n > 0
}

deny contains msg if {
	some path, n in offending
	msg := sprintf("K2: the retired mark appears %d× in %s", [n, path])
}

admitted contains c.path if {
	some c in input.cases
	not offending[c.path]
}
