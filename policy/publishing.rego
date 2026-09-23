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
	contains(r.venue, "KDE Store")
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	not input.listing
	msg := "B2: no cached OCS listing (catalog/ocs-categories.xml); run --refresh once online"
}

deny contains msg if {
	input.listing
	some r in store_rows
	some i in r.ids
	not i.listed
	msg := sprintf("B2: %s: id %s is not in the OCS listing", [r.emitter, i.id])
}

deny contains msg if {
	some r in store_rows
	r.guessed
	msg := sprintf("B2: %s: guessed id in %q", [r.emitter, r.route])
}

admitted contains c.emitter if {
	some c in input.cases
	c.rows > 0
}
