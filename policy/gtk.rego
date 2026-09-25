# METADATA
# title: "K0 — no sheets measured admits nothing; every declared variant is measured"
# description: |
#   The measurement is `scripts/check_gtk.py --json`: the declared roster
#   (make_schemes.GRID), make_gtk.VARIANTS' drift from it, the number of bg/fg
#   pairs check_gtk declares, and per variant what gtk4.css and gtk3.css SAY —
#   tinycss2's parse-error count (null when tinycss2 is absent), the gtk4 --names
#   not in make_gtk.ADW_NAMED (the libadwaita reference, 2026-09-21), the gtk3
#   @define-color names not in GTK3_DEFINES, each value that is not its role, and
#   per declared pair whether both variables are present and their WCAG ratio.
#   Weakness: ADW_NAMED is a snapshot; GNOME is not run here.
package el.gtk

import data.el.fmt
import rego.v1

deny contains "K0: no sheets were measured; the roster is empty, not the sheets sound" if {
	count(object.get(input, "cases", [])) == 0
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	some v in object.get(input, "roster", [])
	not v in {c.id | some c in input.cases}
	msg := sprintf("K0: %s: declared but not measured", [v])
}

deny contains msg if {
	some d in object.get(input, "roster_drift", [])
	msg := sprintf("K0: %s: %s", [d.variant, d.why])
}

# a variant that reports fewer pairs than the check declares shrank its population (W65)
deny contains msg if {
	some c in input.cases
	is_number(input.pairs_declared)
	count(object.get(c, "pairs", [])) != input.pairs_declared
	msg := sprintf("K0: %s: %d pair(s) measured of %d declared", [c.id, count(object.get(c, "pairs", [])), input.pairs_declared])
}

# METADATA
# title: "K1 — the sheets parse"
deny contains msg if {
	some c in input.cases
	is_number(c.parse_errors)
	c.parse_errors > 0
	msg := sprintf("K1: %s: %d parse error(s)", [c.id, c.parse_errors])
}

withheld contains msg if {
	some c in input.cases
	c.parse_errors == null
	msg := sprintf("K1: %s: tinycss2 is not installed here; the parse is unmeasured", [c.id])
}

# METADATA
# title: "K2 — every name is a documented one (session 14: a typo parses and does nothing)"
deny contains msg if {
	some c in input.cases
	is_array(c.unknown_gtk4)
	count(c.unknown_gtk4) > 0
	msg := sprintf("K2: %s: gtk4.css sets undocumented libadwaita variable(s) %v", [c.id, c.unknown_gtk4])
}

deny contains msg if {
	some c in input.cases
	is_array(c.unknown_gtk3)
	count(c.unknown_gtk3) > 0
	msg := sprintf("K2: %s: gtk3.css defines unknown colour(s) %v", [c.id, c.unknown_gtk3])
}

# METADATA
# title: "K3 — every value is the palette role the table names"
deny contains msg if {
	some c in input.cases
	is_array(c.wrong_values)
	some w in c.wrong_values
	msg := sprintf("K3: %s: %s = %v, not its role %s = %v", [c.id, w.name, w.got, w.role, w.want])
}

# METADATA
# title: "K4 — every declared bg/fg pair is present and clears its floor"
deny contains msg if {
	some c in input.cases
	some p in object.get(c, "pairs", [])
	p.present == false
	msg := sprintf("K4: %s: %s on %s: pair absent from gtk4.css", [c.id, p.fg, p.bg])
}

deny contains msg if {
	some c in input.cases
	some p in object.get(c, "pairs", [])
	p.present == true
	is_number(p.ratio)
	is_number(p.floor)
	p.ratio < p.floor
	msg := sprintf("K4: %s: %s on %s is %s:1, under %s:1", [c.id, p.fg, p.bg, fmt.fixed(p.ratio, 2), fmt.fixed(p.floor, 2)])
}

# exactly-once: an unread fact is withheld, never judged
unmeasured(c) := {k |
	some k in ["unknown_gtk4", "unknown_gtk3", "wrong_values", "pairs"]
	not is_array(object.get(c, k, null))
} | {sprintf("pair %v ratio", [object.get(p, "fg", null)]) |
	some p in object.get(c, "pairs", [])
	object.get(p, "present", null) == true
	not is_number(object.get(p, "ratio", null))
} | {sprintf("pair %v present", [object.get(p, "fg", null)]) |
	some p in object.get(c, "pairs", [])
	not is_boolean(object.get(p, "present", null))
}

withheld contains msg if {
	some c in input.cases
	some k in unmeasured(c)
	msg := sprintf("W: %s: %s was not measured", [c.id, k])
}

denied_ids contains c.id if {
	some c in input.cases
	some m in deny
	contains(m, sprintf(": %s:", [c.id]))
}

admitted contains c.id if {
	some c in input.cases
	count(unmeasured(c)) == 0
	not c.id in denied_ids
}
