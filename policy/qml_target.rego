# METADATA
# title: "Q0 — a staged package population with no package admits nothing"
# description: |
#   The measurement is `scripts/check_qml_target.py --json`: every QML package the .deb
#   stages (plasmoid, wallpaper, tabbox, sddm, splash), loaded offscreen under the
#   operator's Qt by luthen's `checks.qml_check` (the tabbox kind under its kwin-tabbox
#   host). A case is {id, kind, entry, digest, shared_with, state, step, withheld}: state
#   is luthen's verdict ("ok" or a failure naming its step), `withheld` the reason the
#   runner could not run at all (no `sg` group, no image, no verdict).
#   Origin: the `var byte` .deb (2026-09-26) passed every gate here on host Qt 6.11.2 and
#   failed on the laptop's Qt 6.10.2.
#   Weakness: an offscreen load proves the document instantiates under the target Qt with
#   the target modules, not that a live Plasma shell would host it.
# custom:
#   family: gate
package el.qml_target

import rego.v1

cases := object.get(input, "cases", [])

deny contains "Q0: no staged QML package was measured; the stage is broken, not the tree clean" if {
	count(cases) == 0
}

# METADATA
# title: "Q1 — every measured package loads under the operator's Qt"
deny contains msg if {
	some c in cases
	not is_withheld(c)
	c.state != "ok"
	msg := sprintf("Q1: %v (%v) fails under the operator's Qt at step %v", [c.id, c.kind, object.get(c, "step", "?")])
}

# METADATA
# title: "Q2 — a package with no verdict is withheld, never passed"
deny contains msg if {
	some c in cases
	not is_withheld(c)
	object.get(c, "state", null) == null
	msg := sprintf("Q2: %v (%v) carries neither a verdict nor a reason it has none", [c.id, c.kind])
}

withheld contains msg if {
	some c in cases
	is_withheld(c)
	msg := sprintf("Q3: %v (%v) was not measured: %v", [c.id, c.kind, c.withheld])
}

is_withheld(c) if {
	is_string(object.get(c, "withheld", null))
	c.withheld != ""
}

# one case per package: admitted when luthen's runner said ok. A withheld package beside
# admitted ones is a SKIP; the same reading with nothing admitted stays withheld.
admitted contains c.id if {
	some c in cases
	not is_withheld(c)
	c.state == "ok"
}
