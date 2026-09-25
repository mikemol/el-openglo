package el.terminals_test

import data.el.terminals as p
import rego.v1

cell(f, v) := {"id": concat(" ", [f, v]), "variant": v, "format": f, "parse_error": null, "mismatches": []}

good := {"variants": ["EL-Openglo"], "formats": ["alacritty", "foot"], "drift": [],
	"cases": [cell("alacritty", "EL-Openglo"), cell("foot", "EL-Openglo")]}

test_admits_faithful_emissions if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	p.admitted == {"alacritty EL-Openglo", "foot EL-Openglo"} with input as good
}

test_r0_refuses_an_absent_population if {
	some m in p.deny with input as {}
	startswith(m, "R0: no emission")
}

test_r0_refuses_drift_either_way if {
	inp := object.union(good, {"drift": [{"format": "kitty", "why": "this check reads it but make_konsole no longer declares it"}]})
	"R0: kitty: this check reads it but make_konsole no longer declares it" in p.deny with input as inp
}

# W65: dropping a cell used to take "30 of 30" to "24 of 24", exit 0 both times
test_r0_refuses_a_declared_cell_not_measured if {
	inp := object.union(good, {"variants": ["EL-Openglo", "EL-Amber"]})
	"R0: alacritty EL-Amber: declared but not measured" in p.deny with input as inp
}

test_r1_refuses_a_parse_failure if {
	c := object.union(cell("alacritty", "EL-Openglo"), {"parse_error": "TOMLDecodeError: Expected ']'", "mismatches": null})
	inp := object.union(good, {"cases": [c, cell("foot", "EL-Openglo")]})
	"R1: alacritty EL-Openglo: does not parse as alacritty: TOMLDecodeError: Expected ']'" in p.deny with input as inp
	not "alacritty EL-Openglo" in p.admitted with input as inp
}

test_r2_refuses_a_swapped_colour if {
	c := object.union(cell("windows-terminal", "EL-Openglo"), {"mismatches": [{"role": "b1", "want": "#ff5555", "got": "#55ff55"}]})
	inp := {"variants": ["EL-Openglo"], "formats": ["windows-terminal"], "drift": [], "cases": [c]}
	"R2: windows-terminal EL-Openglo: 1 role(s) differ from ansi_table: b1 #ff5555!=#55ff55" in p.deny with input as inp
}

test_all_null_case_withheld_only if {
	c := {"id": "foot EL-Openglo", "variant": "EL-Openglo", "format": "foot", "parse_error": null, "mismatches": null}
	inp := {"variants": ["EL-Openglo"], "formats": ["foot"], "drift": [], "cases": [c]}
	"W: foot EL-Openglo: mismatches was not measured" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
	count(p.admitted) == 0 with input as inp
}
