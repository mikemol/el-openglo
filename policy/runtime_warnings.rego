# METADATA
# title: "R0 — an empty corpus admits nothing"
# description: |
#   The measurement is `scripts/check_runtime_warnings.py --json` (W53): one case
#   per class of shell warning the live host has produced.
package el.runtime_warnings

import rego.v1

import data.el.truth

cases := object.get(input, "cases", [])

deny contains "R0: no runtime-warning class was measured" if {
	count(cases) == 0
	not truth.py(object.get(input, "withheld", null))
}

# METADATA
# title: "R1 — a class is ruled, or says since when it is not"
deny contains msg if {
	some c in cases
	c.ruled == false
	not truth.py(object.get(c, "unruled_since", null))
	msg := sprintf("R1: %v has no rule and no unruled_since date", [c["class"]])
}

# METADATA
# title: "R2 — no class stays unruled past the declared limit"
# description: |
#   The tripwire's point: a warning the shell raises late must become a gate rule
#   that raises it at emit time; one left unruled longer than max_unruled_days is
#   refused, which turns it into work.
deny contains msg if {
	some c in cases
	c.ruled == false
	is_number(c.unruled_days)
	is_number(input.max_unruled_days)
	c.unruled_days > input.max_unruled_days
	msg := sprintf("R2: %v unruled for %v days (limit %v)", [c["class"], c.unruled_days, input.max_unruled_days])
}

# METADATA
# title: "R3 — a cited rule's file exists"
deny contains msg if {
	some c in cases
	c.ruled == true
	c.rule_file_exists == false
	msg := sprintf("R3: %v cites %v, which does not exist", [c["class"], c.rule_file])
}

withheld contains msg if {
	truth.py(object.get(input, "withheld", null))
	msg := sprintf("R4: the corpus was not read: %v", [input.withheld])
}
