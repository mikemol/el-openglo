# METADATA
# title: "N0 — no themes measured admits nothing; every declared variant is measured"
# description: |
#   The measurement is `scripts/check_windows.py --json`: the declared roster
#   (make_schemes.GRID), make_windows.VARIANTS' drift from it, and per variant the
#   emitted .theme read back — its parse error, sections, MTSM tag, each
#   [Control Panel\Colors] key beside the `R G B` its palette role wants,
#   ColorizationColor beside the accent's RRGGBB, and whether the referenced
#   wallpaper exists beside it. Weakness: Microsoft's format page, not Windows.
package el.windows

import rego.v1

# the sections without which "the system ignores your Theme"
required := {"Control Panel\\Desktop", "VisualStyles", "MasterThemeSelector"}

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := sprintf("N0: no themes were measured (%v); the search is broken, not the themes valid", [object.get(input, "error", null)])
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	some v in input.roster
	not v in {c.id | some c in input.cases}
	msg := sprintf("N0: %s: declared but not measured", [v])
}

deny contains msg if {
	some c in input.cases
	object.get(c, "missing", null) != null
	msg := sprintf("N0: %s: %s", [c.id, c.missing])
}

deny contains msg if {
	some d in object.get(input, "roster_drift", [])
	msg := sprintf("N0: %s: %s", [d.variant, d.why])
}

# METADATA
# title: "N1 — the theme parses as INI"
deny contains msg if {
	some c in present
	c.parse_error != null
	msg := sprintf("N1: %s: does not parse: %s", [c.id, c.parse_error])
}

# METADATA
# title: "N2 — the three required sections are present, with MTSM=DABJDKT"
deny contains msg if {
	some c in parsed
	lost := required - {s | some s in c.sections}
	count(lost) > 0
	msg := sprintf("N2: %s: missing required section(s) %v", [c.id, sort(lost)])
}

deny contains msg if {
	some c in parsed
	"MasterThemeSelector" in c.sections
	c.mtsm != "DABJDKT"
	msg := sprintf("N2: %s: MTSM is %v, not DABJDKT", [c.id, c.mtsm])
}

# METADATA
# title: "N3 — every [Control Panel\\Colors] value is its palette role, as R G B"
deny contains msg if {
	some c in parsed
	some x in c.colors
	x.got != x.want
	msg := sprintf("N3: %s: %s=%v != %s (%s)", [c.id, x.key, x.got, x.want, x.role])
}

# METADATA
# title: "N4 — ColorizationColor is the accent as 0xAARRGGBB"
deny contains msg if {
	some c in parsed
	not accent_ok(c)
	msg := sprintf("N4: %s: ColorizationColor is %v, not 0xAA%s", [c.id, c.colorization, c.accent])
}

# METADATA
# title: "N5 — the referenced wallpaper exists beside the theme"
deny contains msg if {
	some c in parsed
	c.wallpaper_exists != true
	msg := sprintf("N5: %s: wallpaper %v is not beside the theme", [c.id, c.wallpaper])
}

present contains c if {
	some c in input.cases
	object.get(c, "missing", null) == null
}

parsed contains c if {
	some c in present
	c.parse_error == null
}

accent_ok(c) if {
	c.colorization != null
	c.accent != null
	u := upper(c.colorization)
	startswith(u, "0X")
	count(u) == 10
	endswith(u, c.accent)
}

admitted contains c.id if {
	some c in parsed
	count(required - {s | some s in c.sections}) == 0
	c.mtsm == "DABJDKT"
	every x in c.colors {
		x.got == x.want
	}
	accent_ok(c)
	c.wallpaper_exists == true
}
