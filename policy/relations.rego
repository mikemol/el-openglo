# METADATA
# title: "R0 — no relations measured admits nothing"
# description: |
#   The measurement is `scripts/check_relations.py --json`: every relation in
#   palette_relations (u, v, kind, quantity, bound), the nodes the edge authority
#   declares (palette_graph.declared_nodes), the pinned terminals, the free nodes
#   (INTERIOR, DISCRETE) and the DERIVED ones, the netlist handoff's edges, and the number of
#   open questions. This gates that the relations are WELL-FORMED and CONSUMABLE,
#   not that they are TRUE of the palette (@SEPARATION, @GHOST, @MARGIN do that).
package el.relations

import rego.v1

kinds := {"floor", "ceiling", "balance", "arrow"}

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "R0: no relations declared; the statement is empty, not the palette free"
}

# METADATA
# title: "R1 — a relation names only declared nodes"
# description: |
#   A relation naming a role the authority does not declare would make the
#   relations a FOURTH namespace.
deny contains msg if {
	some r in input.cases
	some side in [r.u, r.v]
	not side in {n | some n in input.known}
	msg := sprintf("R1: %s~%s (%s): names %q, which the edge authority does not", [r.u, r.v, r.kind, side])
}

# METADATA
# title: "R2 — every relation is declarative: a known kind, a quantity, a bound where it bounds"
deny contains msg if {
	some r in input.cases
	not r.kind in kinds
	msg := sprintf("R2: %s~%s: kind %q is not one of floor/ceiling/balance/arrow", [r.u, r.v, r.kind])
}

deny contains msg if {
	some r in input.cases
	r.kind in {"floor", "ceiling"}
	object.get(r, "bound", null) in {null, "", false}
	msg := sprintf("R2: %s~%s: a %s relation with no bound cannot be checked", [r.u, r.v, r.kind])
}

deny contains msg if {
	some r in input.cases
	r.quantity == ""
	msg := sprintf("R2: %s~%s: names no quantity, so nothing says WHAT must hold", [r.u, r.v])
}

# METADATA
# title: "R3 — terminals are declared, and pinned is not free"
deny contains msg if {
	some t in input.terminals
	not t in {n | some n in input.known}
	msg := sprintf("R3: terminal %q is not a declared node", [t])
}

deny contains msg if {
	some t in input.terminals
	t in {n | some n in input.free}
	msg := sprintf("R3: %q is pinned AND free — a node cannot be both", [t])
}

# METADATA
# title: "R4 — every free node is reached by some relation"
# description: |
#   A role added to the palette and never constrained is undetermined, and
#   nothing else says so.
deny contains msg if {
	some n in array.concat(input.free, object.get(input, "derived", []))
	not n in {s | some r in input.cases; some s in [r.u, r.v]}
	msg := sprintf("R4: %q is free but no relation reaches it — undetermined", [n])
}

# METADATA
# title: "R5 — the netlist handoff is the shape the solver consumes"
deny contains msg if {
	count(object.get(input, "netlist", [])) == 0
	msg := "R5: the netlist handoff is empty; nothing could be solved"
}

deny contains msg if {
	some e in input.netlist
	not e.pair
	msg := sprintf("R5: netlist key %s is not a (u, v) pair", [e.key])
}

deny contains msg if {
	some e in input.netlist
	e.generator == ""
	msg := sprintf("R5: netlist edge %s has no generator name", [e.key])
}

# METADATA
# title: "R6 — the gaps are recorded"
# description: |
#   A relation set claiming to determine everything is the overclaim this
#   check exists to avoid; open_questions() must be non-empty.
deny contains msg if {
	object.get(input, "open_questions", 0) == 0
	msg := "R6: no open questions recorded; a relation set that hides its gaps reads as finished"
}

admitted contains sprintf("%s~%s:%s", [r.u, r.v, r.kind]) if {
	some r in input.cases
	r.u in {n | some n in input.known}
	r.v in {n | some n in input.known}
	r.kind in kinds
	r.quantity != ""
}
