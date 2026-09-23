# METADATA
# title: "R0 — no declared population admits nothing"
# description: |
#   The measurement is `scripts/check_readme.py --json`: every item the tree
#   DECLARES (emitters.ROLES, render_screens.VARIANTS and plan_all(),
#   check_symbol.CLOSED) and whether README.md names it. An empty population is
#   a broken search, not a covered README.
package el.readme

import rego.v1

deny contains msg if {
	count(object.get(input, "items", [])) == 0
	msg := "R0: no declared population was measured"
}

# METADATA
# title: "R0 — every population kind is present"
# description: |
#   A kind with no items means its authority stopped answering; the other kinds
#   passing must not hide that.
deny contains msg if {
	count(object.get(input, "items", [])) > 0
	some kind in {"emitter", "variant", "picture", "symbol"}
	count([i | some i in input.items; i.kind == kind]) == 0
	msg := sprintf("R0: no %s was measured", [kind])
}

# METADATA
# title: "R1 — README.md exists"
deny contains msg if {
	count(object.get(input, "items", [])) > 0
	not input.readme
	msg := "R1: README.md is absent"
}

# METADATA
# title: "R2 — the front page names every declared item"
# description: |
#   The old README named 10 of 16 emitters, 2 of 56 pictures and no variant. A
#   projection cannot drift from its claim graph; this is what holds the claim
#   graph to the tree.
deny contains msg if {
	some i in input.items
	not i.named
	msg := sprintf("R2: README.md does not name %s %s", [i.kind, i.name])
}

# METADATA
# title: "R3 — every population fragment is current with its authority"
# description: |
#   catalog/readme/* is written by scripts/readme_fragments.py --write; a
#   fragment that lags its authority would put a stale table on the front page.
deny contains msg if {
	some f in object.get(input, "fragments", [])
	not f.current
	msg := sprintf("R3: catalog/readme/%s is stale — run scripts/readme_fragments.py --write", [f.name])
}

# METADATA
# title: "R4 — render_screens.VARIANTS is the roster (make_schemes.GRID)"
# description: |
#   The variant population, the palette columns and the gallery sections are read
#   from the ROSTER; the screen renderer's own list is compared to it, so a
#   renderer that drops a variant is a deny, not a gallery that quietly lacks a
#   section (W61 R1).
deny contains msg if {
	some d in object.get(input, "roster_drift", [])
	msg := sprintf("R4: %s %s", [d.variant, d.why])
}

deny contains msg if {
	count(object.get(input, "items", [])) > 0
	count(object.get(input, "fragments", [])) == 0
	msg := "R3: no fragment was measured"
}
