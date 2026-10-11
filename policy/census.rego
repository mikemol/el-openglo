# METADATA
# title: "N0 — no tracked file measured admits nothing"
# description: |
#   The measurement is `scripts/check_census.py --json`: every tracked file, and whether it is a named
#   input of some gate stage (present in the census stage's runfiles, whose `data` is the union of
#   every stage's inputs) or declared exempt in gate/census_exempt.tsv with a reason (W488, operator
#   rule 2026-10-06: a tracked gated file missing from the list must itself fail the gate). Outside
#   bazel there is no declaration to compare against: withheld, never admitted.
package el.census

import rego.v1

# an ABSENT population is empty too (`not input.checked == false` holds when `checked` is absent);
# only an explicit checked == false is the withheld case
deny contains msg if {
	not input.checked == false
	count(object.get(input, "cases", [])) == 0
	msg := "N0: no tracked file was measured; the population is empty, not the tree faithfully named"
}

# METADATA
# title: "N1 — a tracked file no stage names"
deny contains msg if {
	some c in object.get(input, "cases", [])
	c.status == "unnamed"
	msg := sprintf("N1: %s is tracked and no stage names it; add it to a stage's inputs or declare it exempt with a reason in gate/census_exempt.tsv", [c.path])
}

# METADATA
# title: "N2 — an exemption without a reason"
deny contains msg if {
	some c in object.get(input, "cases", [])
	c.status == "unreasoned"
	msg := sprintf("N2: %s is exempt with no reason; an exemption is data the reader can judge", [c.path])
}

# METADATA
# title: "N3 — an exemption for a file that is named after all"
deny contains msg if {
	some c in object.get(input, "cases", [])
	c.status == "stale"
	msg := sprintf("N3: %s is exempt (%s) but a stage names it; drop the stale exemption", [c.path, c.reason])
}

# METADATA
# title: "N4 — an exemption for a file that is not tracked"
deny contains msg if {
	some c in object.get(input, "cases", [])
	c.status == "gone"
	msg := sprintf("N4: %s is exempt but not tracked; drop the exemption", [c.path])
}

# METADATA
# title: "W — not under bazel: a fact about how this was run"
withheld contains msg if {
	input.checked == false
	msg := sprintf("W: %s", [input.withheld])
}

admitted contains c.path if {
	some c in object.get(input, "cases", [])
	c.status in {"named", "exempt"}
}
