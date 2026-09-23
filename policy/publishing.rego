# METADATA
# title: "B0 — an empty emitter population or an empty table admits nothing"
# description: |
#   The measurement is `scripts/check_publishing.py --json`: every emitter
#   (emitters.ORDER plus the render_all() emitters make_deb drives, minus
#   make_preview) with how many rows of catalog/publishing.md name it; every
#   table row with its venue, the KDE Store ids its route cites (each marked
#   listed or not in the cached OCS listing), and whether the route carries a
#   '?'; and whether the cached listing was present at all.
package el.publishing

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "B0: no emitter was measured; the roster is broken, not every target routed"
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	count(object.get(input, "rows", [])) == 0
	msg := "B0: catalog/publishing.md has no rows"
}

# METADATA
# title: "B1 — every emitter has at least one publishing row"
# description: |
#   A new target must not ship without a stated route.
deny contains msg if {
	some c in input.cases
	c.rows == 0
	msg := sprintf("B1: %s has no row in catalog/publishing.md", [c.emitter])
}

# METADATA
# title: "B2 — every KDE Store id the table cites exists, and none is a guess"
# description: |
#   A number must not outlive the store's taxonomy unnoticed. The cached
#   listing IS the measurement (dated; --refresh re-fetches it), so a missing
#   cache is a deny, not a pass: the ids cannot be confirmed and the table
#   would otherwise go green on nothing. A route marked '?' is a guessed id.
#   Weakness: an id that EXISTS is not an id that is RIGHT for the artifact.
store_rows contains r if {
	some r in input.rows
	is_string(r.venue)
	contains(r.venue, "KDE Store")
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	input.listing == false
	msg := "B2: no cached OCS listing (catalog/ocs-categories.xml); run --refresh once online"
}

deny contains msg if {
	input.listing == true
	some r in store_rows
	some i in r.ids
	i.listed == false
	msg := sprintf("B2: %s: id %s is not in the OCS listing", [r.emitter, i.id])
}

deny contains msg if {
	some r in store_rows
	r.guessed == true
	msg := sprintf("B2: %s: guessed id in %q", [r.emitter, r.route])
}

admitted contains c.emitter if {
	some c in input.cases
	is_number(c.rows)
	c.rows > 0
}

# ⚑ EXACTLY ONCE: the measurement always emits `listing` (bool), per emitter
# `rows` (a count), per table row `venue` (str) and `guessed` (bool), and per
# cited id `listed` (bool). One of those null or absent is a could-not-say:
# WITHHELD by name, judged by no rule (`not input.listing` read null as a
# listing present, `not i.listed` read null as listed).
withheld contains msg if {
	count(object.get(input, "cases", [])) > 0
	not is_boolean(object.get(input, "listing", null))
	msg := "B2: listing was not measured"
}

withheld contains msg if {
	some c in object.get(input, "cases", [])
	not is_number(object.get(c, "rows", null))
	msg := sprintf("B1: %v: rows was not measured", [object.get(c, "emitter", null)])
}

withheld contains msg if {
	some r in object.get(input, "rows", [])
	not is_string(object.get(r, "venue", null))
	msg := sprintf("B2: %v: venue was not measured", [object.get(r, "emitter", null)])
}

withheld contains msg if {
	some r in store_rows
	not is_boolean(object.get(r, "guessed", null))
	msg := sprintf("B2: %v: guessed was not measured", [r.emitter])
}

withheld contains msg if {
	some r in store_rows
	not is_array(object.get(r, "ids", null))
	msg := sprintf("B2: %v: ids was not measured", [r.emitter])
}

withheld contains msg if {
	input.listing == true
	some r in store_rows
	some i in object.get(r, "ids", [])
	not is_boolean(object.get(i, "listed", null))
	msg := sprintf("B2: %v: id %v: listed was not measured", [r.emitter, object.get(i, "id", null)])
}
