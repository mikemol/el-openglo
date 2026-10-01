# METADATA
# title: "P0 — an install with no shipped package admits nothing"
# description: |
#   The measurement is `scripts/check_plugin_ids.py --json` (W171): over the tree
#   make_deb.stage() lays down, every package metadata.json (its KPlugin.Id and
#   directory) and every org.el.* id the staged text references. No shipped package
#   means the stage or the walk broke, not that nothing is referenced.
package el.plugin_ids

import rego.v1

import data.el.truth

shipped := object.get(input, "shipped", [])

referenced := object.get(input, "referenced", [])

shipped_ids := {s.id | some s in shipped}

deny contains "P0: no shipped package was measured; the stage or the walk is broken" if {
	count(shipped) == 0
	not truth.py(object.get(input, "withheld", null))
}

# METADATA
# title: "P1 — a package's KPlugin.Id is its directory name"
# description: |
#   Plasma finds a package by directory; an Id that differs loads under neither name
#   reliably.
deny contains msg if {
	some s in shipped
	s.dir_matches == false
	msg := sprintf("P1: %v/%v declares Id %v, not its directory name", [s.kind, s.dir, s.id])
}

# METADATA
# title: "P2 — every referenced id is one a shipped package declares"
# description: |
#   The f521e6f shape (operator, 2026-09-22: "My plasma didn't come up at all!"): a
#   desktop naming org.el.openglo.live.elazure after the one-package build stopped
#   shipping it, and a missing wallpaper plugin fails the shell. A PREFIX (an id the
#   referencing script completes at run time) is satisfied when some shipped id
#   extends it. `prefix` is always measured as a boolean; a null one is withheld
#   (P3), never judged.
satisfied(r) if {
	r.prefix == false
	r.id in shipped_ids
}

satisfied(r) if {
	r.prefix == true
	some s in shipped_ids
	startswith(s, concat("", [r.id, "."]))
}

deny contains msg if {
	some r in referenced
	is_boolean(object.get(r, "prefix", null))
	not satisfied(r)
	msg := sprintf("P2: %v references %v%v, which no shipped package declares", [r.file, r.id, prefix_mark(r)])
}

prefix_mark(r) := ".* (a run-time prefix)" if r.prefix == true

prefix_mark(r) := "" if r.prefix == false

withheld contains msg if {
	some r in referenced
	not is_boolean(object.get(r, "prefix", null))
	msg := sprintf("P3: %v in %v: whether it is a prefix was not measured", [object.get(r, "id", null), object.get(r, "file", null)])
}

withheld contains msg if {
	truth.py(object.get(input, "withheld", null))
	msg := sprintf("P3: %v", [input.withheld])
}
