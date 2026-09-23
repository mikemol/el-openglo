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
	c.defaults_ok == false
	msg := sprintf("I4: %s: the LnF defaults do not select the emitted theme names", [c.id])
}

withheld contains msg if {
	some c in measured
	some p, ok in c.installed
	ok == false
	msg := sprintf("I5: %s: parent %q is not installed on this host", [c.id, p])
}

withheld contains msg if {
	some c in measured
	some p, ok in c.installed
	not is_boolean(ok)
	msg := sprintf("I6: %s: whether parent %q is installed was not measured", [c.id, p])
}

# METADATA
# title: "I6 — a variant the measurement could not describe is withheld, not judged"
# description: |
#   The measurement always emits `missing` (null or a reason) and, for a read
#   variant, `icon_parents` / `icon_dirs` (lists), `cursor_parent` (string),
#   `defaults_ok` (bool) and `installed` (object). A null in any of them is
#   "could not say": before this, a null `icon_parents` was DENIED by I1 and a
#   null `defaults_ok` was neither denied nor admitted.
withheld contains msg if {
	some c in input.cases
	not "missing" in object.keys(c)
	msg := sprintf("I6: %v: missing was not measured", [object.get(c, "id", null)])
}

withheld contains msg if {
	some c in read
	some f in unmeasured(c)
	msg := sprintf("I6: %v: %s was not measured", [object.get(c, "id", null), f])
}

# read: the measurement reached the variant; measured: and described it fully
read contains c if {
	some c in input.cases
	"missing" in object.keys(c)
	c.missing == null
}

unmeasured(c) := {f |
	some f, ok in {
		"icon_parents": is_array(object.get(c, "icon_parents", null)),
		"icon_dirs": is_array(object.get(c, "icon_dirs", null)),
		"cursor_parent": is_string(object.get(c, "cursor_parent", null)),
		"defaults_ok": is_boolean(object.get(c, "defaults_ok", null)),
		"installed": is_object(object.get(c, "installed", null)),
	}
	ok == false
}

measured contains c if {
	some c in read
	count(unmeasured(c)) == 0
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
	c.defaults_ok == true
}
