# METADATA
# title: "C0 — an unmeasured cursor theme admits nothing"
# description: |
#   The measurement is `scripts/check_cursors.py --json`: per variant, the
#   phosphor cursor theme make_cursors emits (W36) read back as XCursor files —
#   each entry's link target, nominal sizes, and dominant opaque colours at 32 px,
#   beside the variant's solved tokens (parse_scheme phosphor + ground).
package el.cursors

import rego.v1

cases := object.get(input, "cases", [])

deny contains msg if {
	count(cases) == 0
	msg := "C0: no cursor theme was measured"
}

measured contains c if {
	some c in cases
	not c.withheld
}

# the core shapes — the names a desktop asks for most, drawn (not inherited)
core_shapes := {
	"default", "text", "pointer", "wait", "progress", "crosshair", "not-allowed",
	"ew-resize", "ns-resize", "nwse-resize", "nesw-resize", "move",
}

# the aliases KDE (Qt), GTK (CSS names) and legacy X11 look the core shapes up by
core_aliases := {
	"left_ptr", "arrow", "xterm", "ibeam", "hand2", "hand1", "pointing_hand",
	"watch", "left_ptr_watch", "half-busy", "cross", "tcross", "forbidden",
	"crossed_circle", "no-drop", "e-resize", "w-resize", "col-resize",
	"sb_h_double_arrow", "size_hor", "n-resize", "s-resize", "row-resize",
	"sb_v_double_arrow", "size_ver", "nw-resize", "se-resize", "size_fdiag",
	"ne-resize", "sw-resize", "size_bdiag", "all-scroll", "fleur", "size_all",
	"top_left_corner", "top_right_corner", "bottom_left_corner", "bottom_right_corner",
}

required_sizes := {24, 32, 48}

usable(c, name) if {
	c.entries[name].readable
}

# C1 — a core shape is missing or unreadable
deny contains msg if {
	some c in measured
	some s in core_shapes
	not usable(c, s)
	msg := sprintf("C1: %s lacks the core shape %s", [c.id, s])
}

# C2 — an alias is missing or does not resolve to a readable cursor
deny contains msg if {
	some c in measured
	some a in core_aliases
	not usable(c, a)
	msg := sprintf("C2: %s lacks the alias %s", [c.id, a])
}

# C3 — a glyph's dominant colour is not its variant's token (lit or ground)
deny contains msg if {
	some c in measured
	some name, e in c.entries
	e.readable
	some col in e.dominant
	not col in {c.tokens.lit, c.tokens.ground}
	msg := sprintf("C3: %s %s is drawn in %s, not its tokens lit=%s ground=%s", [c.id, name, col, c.tokens.lit, c.tokens.ground])
}

# C3 — and a readable glyph that drew nothing opaque has no colour to check
deny contains msg if {
	some c in measured
	some name, e in c.entries
	e.readable
	count(e.dominant) == 0
	msg := sprintf("C3: %s %s has no opaque pixels at the probe size", [c.id, name])
}

# C4 — every core shape carries every size
deny contains msg if {
	some c in measured
	some s in core_shapes
	usable(c, s)
	missing := required_sizes - {z | some z in c.entries[s].sizes}
	count(missing) > 0
	msg := sprintf("C4: %s %s lacks size(s) %v", [c.id, s, missing])
}

# C5 — the theme has its index.theme (the name and the Inherits= fallback)
deny contains msg if {
	some c in measured
	not c.index_theme
	msg := sprintf("C5: %s has no index.theme", [c.id])
}

admitted contains c.id if {
	some c in measured
	not denied_id(c.id)
}

denied_id(id) if {
	some msg in deny
	contains(msg, sprintf(" %s ", [id]))
}

withheld contains msg if {
	some c in cases
	c.withheld
	msg := sprintf("%s: %s", [c.id, c.withheld])
}
