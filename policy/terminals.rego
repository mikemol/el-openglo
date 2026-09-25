# METADATA
# title: "R0 — every declared (variant, format) emission is measured"
# description: |
#   The measurement is `scripts/check_terminals.py --json`: the declared variants
#   (variant_roster), the formats make_konsole.TERMINAL_FORMATS declares, the drift
#   between those formats and the check's readers in both directions, and per
#   measurable (variant, format) cell the parse error, or the roles whose read-back
#   (with the consumer's own parser) differs from make_konsole.ansi_table.
#   Weakness: the file says what the table says; whether a terminal reads a key is
#   the consumer's schema, checked only by name.
package el.terminals

import rego.v1

deny contains "R0: no emission was measured; the rosters are empty, not the terminals faithful" if {
	count(object.get(input, "cases", [])) == 0
}

# a format emitted with no reader, or a reader for a format no longer emitted
deny contains msg if {
	some d in object.get(input, "drift", [])
	msg := sprintf("R0: %s: %s", [d.format, d.why])
}

# ⚑ THE POPULATION IS A PRODUCT OF DECLARED DIMENSIONS (W65): every declared
# variant x format cell must be measured — n of n is green for every n.
deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	drifted := {d.format | some d in object.get(input, "drift", [])}
	some v in object.get(input, "variants", [])
	some f in object.get(input, "formats", [])
	not f in drifted
	not concat(" ", [f, v]) in {c.id | some c in input.cases}
	msg := sprintf("R0: %s %s: declared but not measured", [f, v])
}

# METADATA
# title: "R1 — every emission parses with its consumer's parser"
deny contains msg if {
	some c in input.cases
	is_string(c.parse_error)
	msg := sprintf("R1: %s: does not parse as %s: %s", [c.id, c.format, c.parse_error])
}

# METADATA
# title: "R2 — every emission carries the one ansi table"
deny contains msg if {
	some c in input.cases
	is_array(c.mismatches)
	count(c.mismatches) > 0
	shown := [sprintf("%s %s!=%v", [m.role, m.want, m.got]) | some m in array.slice(c.mismatches, 0, 3)]
	msg := sprintf("R2: %s: %d role(s) differ from ansi_table: %s", [c.id, count(c.mismatches), concat(", ", shown)])
}

withheld contains msg if {
	some c in input.cases
	c.parse_error == null
	not is_array(c.mismatches)
	msg := sprintf("W: %s: mismatches was not measured", [c.id])
}

admitted contains c.id if {
	some c in input.cases
	c.parse_error == null
	is_array(c.mismatches)
	count(c.mismatches) == 0
}
