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
	measured(c)
	not excluded[c.path]
	n := sum([l.count | some l in c.lines; l.attribution == false])
	n > 0
}

deny contains msg if {
	some path, n in offending
	msg := sprintf("K2: the retired mark appears %d× in %s", [n, path])
}

admitted contains c.path if {
	some c in input.cases
	measured(c)
	not offending[c.path]
}

# measured: the measurement always emits `lines` (a list, [] for a clean file)
# and, per line, `count` (int) and `attribution` (bool). A null anywhere is
# "could not say" — before this a null `lines` summed to 0 and was ADMITTED, and
# a null `attribution` was read as attribution (`not null` is false).
measured(c) if count(unmeasured(c)) == 0

unmeasured(c) := {"lines"} if not is_array(object.get(c, "lines", null))

else := {sprintf("lines[%d].%s", [i, k]) |
	some i, l in c.lines
	some k, ok in {
		"count": is_number(object.get(l, "count", null)),
		"attribution": is_boolean(object.get(l, "attribution", null)),
	}
	ok == false
}

# METADATA
# title: "K3 — a file the measurement could not describe is withheld, not judged"
withheld contains msg if {
	some c in input.cases
	some f in unmeasured(c)
	msg := sprintf("K3: %v: %s was not measured", [object.get(c, "path", null), f])
}
