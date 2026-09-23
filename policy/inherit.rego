# METADATA
# title: "I0 — no variants measured admits nothing; every declared variant is measured"
# description: |
#   The measurement is `scripts/check_inherit.py --json`: the declared roster
#   (make_schemes.GRID via variant_roster) and, per member, the emitted icon
#   theme's Inherits chain and Directories, the cursor theme's parent, whether the
#   LnF defaults fragment selects the emitted names, and which parents are
#   installed under /usr/share/icons on this host — or `missing` with a reason (a
#   declared variant make_inherit does not emit, one it emits the palette does not
#   declare, an index that does not parse). An inheriting theme is only as real as
#   its parent; a parent not installed HERE is withheld, a fact about the host.
package el.inherit

import rego.v1

import data.el.truth

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "I0: no variants were measured; the roster is empty, not the themes well-formed"
}

deny contains msg if {
	some c in input.cases
	c.missing != null
	msg := sprintf("I0: %s: %s", [c.id, c.missing])
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	some v in input.roster
	not v in {c.id | some c in input.cases}
	msg := sprintf("I0: %s: declared but not measured", [v])
}

# METADATA
# title: "I1 — the icon chain ends in hicolor, and follows polarity"
deny contains msg if {
	some c in measured
	not last_is_hicolor(c.icon_parents)
	msg := sprintf("I1: %s: icon Inherits does not end in hicolor (%v)", [c.id, c.icon_parents])
}

deny contains msg if {
	some c in measured
	count(c.icon_parents) > 0
	(c.icon_parents[0] == "breeze") != endswith(c.id, "-Lit")
	msg := sprintf("I1: %s: an Off variant inherits breeze-dark and a Lit one breeze; got %s", [c.id, c.icon_parents[0]])
}

# METADATA
# title: "I2 — the icon theme declares a directory (KIconTheme rejects one that does not)"
deny contains msg if {
	some c in measured
	count(c.icon_dirs) == 0
	msg := sprintf("I2: %s: the icon theme declares no Directories", [c.id])
}

# METADATA
# title: "I3 — the cursor theme names one parent, of the right polarity"
deny contains msg if {
	some c in measured
	c.cursor_parent == ""
	msg := sprintf("I3: %s: the cursor theme names no parent", [c.id])
}

deny contains msg if {
	some c in measured
	c.cursor_parent != ""
	(c.cursor_parent == "breeze_cursors") != endswith(c.id, "-Lit")
	msg := sprintf("I3: %s: dark ground takes light arrows, light ground dark; got %s", [c.id, c.cursor_parent])
}

# METADATA
# title: "I4 — the LnF defaults select the emitted theme names"
deny contains msg if {
	some c in measured
	not c.defaults_ok
	msg := sprintf("I4: %s: the LnF defaults do not select the emitted theme names", [c.id])
}

withheld contains msg if {
	some c in measured
	some p, ok in c.installed
	not ok
	msg := sprintf("I5: %s: parent %q is not installed on this host", [c.id, p])
}

measured contains c if {
	some c in input.cases
	c.missing == null
}

last_is_hicolor(ps) if {
	count(ps) > 0
	ps[count(ps) - 1] == "hicolor"
}

admitted contains c.id if {
	some c in measured
	last_is_hicolor(c.icon_parents)
	count(c.icon_dirs) > 0
	c.cursor_parent != ""
	truth.py(c.defaults_ok)
}
