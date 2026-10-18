# METADATA
# title: "H0 — a hypothesis register with no hypothesis admits nothing"
# description: |
#   A hypothesis marks an ambiguity between the Rego model and the implementation
#   (operator, 2026-10-01): it is testing a question neither side settles. It closes only
#   when BOTH sides are refined at that boundary, never on a verdict alone. A record is
#   {id, status (open|closed), question, rule, structure, boundary}: the question the
#   model and the code both leave open (a), the rule the model gains to decide it (b), the
#   implementation structure that makes the rule checkable (c), and the boundary of that
#   boundary, the edges of the new rule that still hold a fresh ambiguity (d).
#   Pilot: W200 frame-18 tear. Weakness: this judges a record's shape, not whether the
#   named rule is the right one or the structure really makes it checkable; the measurement
#   that reads records from their store is a separate leaf.
# custom:
#   family: gate
package el.hypotheses

import rego.v1

records := object.get(input, "hypotheses", [])

deny contains "H0: no hypothesis was read; the register is unread, not settled" if {
	count(records) == 0
}

# METADATA
# title: "H1 — a hypothesis states the question it tests"
deny contains msg if {
	some h in records
	not is_named(object.get(h, "question", ""))
	msg := sprintf("H1: %v states no question; a hypothesis with none marks no ambiguity", [h.id])
}

# METADATA
# title: "H2 — a closed hypothesis names the rule the model gained"
deny contains msg if {
	some h in records
	h.status == "closed"
	not is_named(object.get(h, "rule", ""))
	msg := sprintf("H2: %v is closed on a verdict alone; the model gained no rule to decide it", [h.id])
}

# METADATA
# title: "H3 — a closed hypothesis names the structure that makes the rule checkable"
deny contains msg if {
	some h in records
	h.status == "closed"
	not is_named(object.get(h, "structure", ""))
	msg := sprintf("H3: %v is closed with no implementation structure that makes its rule checkable", [h.id])
}

# METADATA
# title: "H4 — a closed hypothesis leaves no open boundary"
deny contains msg if {
	some h in records
	h.status == "closed"
	count(object.get(h, "boundary", [])) > 0
	msg := sprintf("H4: %v is closed but its new rule has an open edge: %v", [h.id, h.boundary])
}

withheld contains msg if {
	some h in records
	h.status == "open"
	msg := sprintf("H5: %v is still open; the model and the implementation are not both refined at its boundary", [h.id])
}

is_named(s) if {
	is_string(s)
	trim_space(s) != ""
}

# one case per closed hypothesis that satisfies H1-H4; an open one is withheld beside them
admitted contains h.id if {
	some h in records
	h.status == "closed"
	is_named(object.get(h, "question", ""))
	is_named(object.get(h, "rule", ""))
	is_named(object.get(h, "structure", ""))
	count(object.get(h, "boundary", [])) == 0
}
