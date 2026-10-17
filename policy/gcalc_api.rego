# METADATA
# title: "G0 — no adapter names measured admits nothing"
# description: |
#   The measurement is `scripts/check_gcalc_api.py --json`: every name gcalc_api.NAMES claims the
#   gcalculus sibling defines (resolved by importing the module that should define it) and every
#   attribute a caller reads off the adapter (declared in NAMES or not). gcalculus split its solver
#   into a package of namespaces on 2026-10-09 and four checks died on removed names (W485): this
#   names the moved name instead of a bare AttributeError far from its cause.
# custom:
#   family: gate
package el.gcalc_api

import rego.v1

deny contains msg if {
	count(object.get(input, "names", [])) == 0
	msg := "G0: the adapter names nothing; the population is empty, not the sibling faithfully reached"
}

# METADATA
# title: "G1 — a name the sibling no longer defines"
deny contains msg if {
	input.present == true
	some n in input.names
	n.defined == false
	msg := sprintf("G1: gcalc_api names %s from %s and the sibling does not define it: %s", [n.name, n.module, n.why])
}

# METADATA
# title: "G2 — a caller reads an attribute the adapter does not declare"
deny contains msg if {
	some c in object.get(input, "callers", [])
	c.declared == false
	msg := sprintf("G2: %s:%d reads %s off gcalc_api, which NAMES does not declare", [c.file, c.line, c.name])
}

# METADATA
# title: "W — the sibling is absent: a fact about the machine"
withheld contains msg if {
	input.present == false
	msg := "W: the gcalculus sibling is absent; its names were not resolved (a SKIP, never a pass)"
}

admitted contains n.name if {
	input.present == true
	some n in input.names
	n.defined == true
}

admitted contains sprintf("%s:%d", [c.file, c.line]) if {
	some c in object.get(input, "callers", [])
	c.declared == true
}
