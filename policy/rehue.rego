# METADATA
# title: "H0 — no variants measured admits nothing; every declared variant is measured"
# description: |
#   The measurement is `scripts/check_rehue.py --json` (relations.md §5a): per
#   variant, fg's lit Lc against the ground and the APCA lit floor; per hue bucket
#   of make_palette.hue_table, whether the sender's hue was accepted, that colour's
#   Lc, its worst-view separation from the ghost (normalised, >= 1 separable), and
#   whether it IS fg. Weakness: the table the solver emits, not what the widget
#   paints (check_marquee_live sees pixels).
package el.rehue

import data.el.fmt
import rego.v1

deny contains "H0: no variants were measured; the roster is empty, not the hues gated" if {
	count(object.get(input, "cases", [])) == 0
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	some v in object.get(input, "roster", [])
	not v in {c.id | some c in input.cases}
	msg := sprintf("H0: %s: declared but not measured", [v])
}

# METADATA
# title: "H1 — fg itself clears the lit floor (the fallback must be legal)"
deny contains msg if {
	some c in input.cases
	is_number(c.fg_lc)
	is_number(c.floor)
	c.fg_lc < c.floor
	msg := sprintf("H1: %s: fg itself is under the lit floor (Lc %s < %s)", [c.id, fmt.fixed(c.fg_lc, 1), fmt.fixed(c.floor, 1)])
}

# METADATA
# title: "H2 — an accepted hue clears the lit floor"
deny contains msg if {
	some c in input.cases
	some b in c.buckets
	b.accepted == true
	is_number(b.lc)
	is_number(c.floor)
	b.lc < c.floor
	msg := sprintf("H2: %s: hue %s accepted under the lit floor (Lc %s)", [c.id, fmt.fixed(b.hue, 0), fmt.fixed(b.lc, 1)])
}

# METADATA
# title: "H3 — an accepted hue is separable from the ghost in every view"
deny contains msg if {
	some c in input.cases
	some b in c.buckets
	b.accepted == true
	is_number(b.sep)
	b.sep < 1
	msg := sprintf("H3: %s: hue %s accepted but not separable from the ghost (worst %s < 1)", [c.id, fmt.fixed(b.hue, 0), fmt.fixed(b.sep, 2)])
}

# METADATA
# title: "H4 — a rejected hue falls back to fg, nothing else"
deny contains msg if {
	some c in input.cases
	some b in c.buckets
	b.accepted == false
	b.is_fg == false
	msg := sprintf("H4: %s: hue %s was rejected but did not fall back to fg", [c.id, fmt.fixed(b.hue, 0)])
}

# METADATA
# title: "H5 — the read is alive: some hue is accepted"
deny contains msg if {
	some c in input.cases
	count(c.buckets) > 0
	every b in c.buckets {
		b.accepted == false
	}
	msg := sprintf("H5: %s: every hue falls back — the read is dead", [c.id])
}

deny contains msg if {
	some c in input.cases
	count(object.get(c, "buckets", [])) == 0
	msg := sprintf("H5: %s: no hue buckets were measured", [c.id])
}

# exactly-once: a null measurement is withheld, never judged
unmeasured(c) := {k |
	some k in ["fg_lc", "floor"]
	not is_number(object.get(c, k, null))
} | {sprintf("bucket %v %s", [object.get(b, "hue", null), k]) |
	some b in object.get(c, "buckets", [])
	some k in ["accepted", "is_fg"]
	not is_boolean(object.get(b, k, null))
} | {sprintf("bucket %v %s", [object.get(b, "hue", null), k]) |
	some b in object.get(c, "buckets", [])
	some k in ["lc", "sep"]
	not is_number(object.get(b, k, null))
}

withheld contains msg if {
	some c in input.cases
	some k in unmeasured(c)
	msg := sprintf("W: %s: %s was not measured", [c.id, k])
}

denied_ids contains id if {
	some m in deny
	some c in input.cases
	id := c.id
	contains(m, sprintf(": %s:", [id]))
}

admitted contains c.id if {
	some c in input.cases
	count(unmeasured(c)) == 0
	not c.id in denied_ids
}
