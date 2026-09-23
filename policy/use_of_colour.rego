package el.use_of_colour

# W72 — WCAG 2.2 SC 1.4.1, use of colour. The measurement is
# scripts/check_use_of_colour.py --json; the design is catalog/use-of-colour.md.
# ⚑ Operator ruling 2026-09-23: opacity is colour. Only a channel in non_colour
# is a cue; "hue" and "opacity" never are.

import rego.v1

# first rule: an ABSENT or empty population is a broken search, not a clean tree
deny contains "U0: no colour-bearing conditions measured: the search is broken" if {
	count(object.get(input, "cases", [])) == 0
}

non_colour := {"weight", "text", "shape", "border", "stroke", "halo", "animation", "position"}

cue_kinds(c) := {k | some q in object.get(c, "cues", []); k := q.kind; non_colour[k]}

colour_kinds(c) := {k | some q in object.get(c, "colour", []); k := q.kind}

# a meaning with no non-colour cue: carried by hue and/or opacity alone
deny contains msg if {
	some c in object.get(input, "cases", [])
	count(cue_kinds(c)) == 0
	msg := sprintf("U1: %s %s:%d: '%s' carried by colour alone (%s)",
		[c.id, c.file, c.line, c.meaning, concat("+", sort([k | some k in colour_kinds(c)]))])
}

admitted contains c.id if {
	some c in object.get(input, "cases", [])
	count(cue_kinds(c)) > 0
}

withheld contains msg if {
	some w in object.get(input, "withheld", [])
	msg := sprintf("%s %s: %s", [w.id, w.file, w.reason])
}
