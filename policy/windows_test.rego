package el.windows_test

import data.el.windows as p
import rego.v1

# a trimmed real case (--json, 2026-09-23: EL-Amber, two of its nineteen keys)
amber := {
	"id": "EL-Amber", "missing": null, "parse_error": null,
	"sections": ["Theme", "Control Panel\\Desktop", "Control Panel\\Colors", "VisualStyles", "MasterThemeSelector"],
	"mtsm": "DABJDKT",
	"colors": [
		{"key": "Background", "role": "ground", "got": "31 23 12", "want": "31 23 12"},
		{"key": "WindowText", "role": "phosphor", "got": "255 212 153", "want": "255 212 153"},
	],
	"colorization": "0xC4FAB14B", "accent": "FAB14B",
	"wallpaper": "DesktopBackground\\EL-Amber.png", "wallpaper_exists": true,
}

good := {"roster": ["EL-Amber"], "error": null, "roster_drift": [], "cases": [amber]}

bent(edit) := object.union(good, {"cases": [object.union(amber, edit)]})

test_admits_a_theme_windows_would_list if {
	count(p.deny) == 0 with input as good
	p.admitted == {"EL-Amber"} with input as good
}

test_n0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "N0: no themes were measured")
}

# the real failure (W65, check_discriminates probe windows/variant-roster): an
# emitter that dropped a variant took "30 of 30" to "25 of 25", rc 0
test_n0_refuses_an_emitter_that_drops_a_variant if {
	bad := object.union(good, {"roster_drift": [{"variant": "EL-Openglo-Lit", "who": "make_windows", "why": "make_windows.VARIANTS does not declare it (GRID does)"}]})
	some msg in p.deny with input as bad
	msg == "N0: EL-Openglo-Lit: make_windows.VARIANTS does not declare it (GRID does)"
}

test_n0_refuses_a_declared_variant_not_measured if {
	some msg in p.deny with input as object.union(good, {"roster": ["EL-Amber", "EL-Azure"]})
	msg == "N0: EL-Azure: declared but not measured"
}

# no real N1-N5 denial is recorded; each is the defect the selftest plants
test_n1_refuses_an_unparsable_theme if {
	some msg in p.deny with input as bent({"parse_error": "MissingSectionHeaderError: x"})
	msg == "N1: EL-Amber: does not parse: MissingSectionHeaderError: x"
}

test_n2_refuses_a_missing_section if {
	some msg in p.deny with input as bent({"sections": ["Theme", "Control Panel\\Desktop", "VisualStyle", "MasterThemeSelector"]})
	msg == "N2: EL-Amber: missing required section(s) [\"VisualStyles\"]"
}

test_n2_refuses_a_wrong_mtsm if {
	some msg in p.deny with input as bent({"mtsm": "NOPE"})
	msg == "N2: EL-Amber: MTSM is NOPE, not DABJDKT"
}

test_n3_refuses_an_authored_colour if {
	some msg in p.deny with input as bent({"colors": [{"key": "WindowText", "role": "phosphor", "got": "1 2 3 ;255 212 153", "want": "255 212 153"}]})
	msg == "N3: EL-Amber: WindowText=1 2 3 ;255 212 153 != 255 212 153 (phosphor)"
}

test_n3_refuses_an_absent_colour if {
	some msg in p.deny with input as bent({"colors": [{"key": "WindowText", "role": "phosphor", "got": null, "want": "255 212 153"}]})
	msg == "N3: EL-Amber: WindowText=null != 255 212 153 (phosphor)"
}

test_n4_refuses_a_wrong_accent if {
	some msg in p.deny with input as bent({"colorization": "0x00C4FAB14B"})
	msg == "N4: EL-Amber: ColorizationColor is 0x00C4FAB14B, not 0xAAFAB14B"
}

test_n4_refuses_an_absent_accent if {
	some msg in p.deny with input as bent({"colorization": null})
	startswith(msg, "N4: EL-Amber: ColorizationColor is null")
}

test_n5_refuses_a_missing_wallpaper if {
	some msg in p.deny with input as bent({"wallpaper_exists": false})
	msg == "N5: EL-Amber: wallpaper DesktopBackground\\EL-Amber.png is not beside the theme"
}
