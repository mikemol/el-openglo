package el.css_test

import data.el.css as p
import rego.v1

mix := "color-mix(in srgb, var(--el-fg-in) 40%, var(--el-view))"

block := {"--el-fg": "rgb(75 250 215)", "--el-view": "rgb(8 20 17)", "--el-fg-in-seen": mix, "--el-fg-in-seen-glanced": mix}

lit := {"--el-fg": "rgb(8 20 17)", "--el-view": "rgb(240 250 248)", "--el-fg-in-seen": mix, "--el-fg-in-seen-glanced": mix}

exp := {"--el-fg": "rgb(75 250 215)", "--el-view": "rgb(8 20 17)"}

exp_lit := {"--el-fg": "rgb(8 20 17)", "--el-view": "rgb(240 250 248)"}

good := {"file_present": true, "parsed": true, "root": block, "light": lit, "cases": [
	{"id": "EL-Openglo", "expected": exp, "got": block},
	{"id": "EL-Openglo-Lit", "expected": exp_lit, "got": lit},
]}

test_admits_a_current_sheet if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 2 with input as good
}

test_k0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "K0:")
}

test_k0_refuses_an_absent_file if {
	some msg in p.deny with input as object.union(good, {"file_present": false})
	msg == "K0: catalog/el-openglo.css absent; run make_css.py"
}

# the old selftest's stale-value fixture: --el-fg rewritten to rgb(0 0 0)
test_k1_refuses_a_stale_value if {
	stale := object.union(block, {"--el-fg": "rgb(0 0 0)"})
	bad := object.union(good, {"root": stale, "cases": [{"id": "EL-Openglo", "expected": exp, "got": stale}, good.cases[1]]})
	some msg in p.deny with input as bad
	msg == "K1: EL-Openglo: --el-fg = \"rgb(0 0 0)\", token says \"rgb(75 250 215)\""
	p.admitted == {"EL-Openglo-Lit"} with input as bad
}

test_k1_refuses_a_missing_key if {
	dropped := object.remove(block, ["--el-view"])
	bad := object.union(good, {"root": dropped, "cases": [{"id": "EL-Openglo", "expected": exp, "got": dropped}, good.cases[1]]})
	some msg in p.deny with input as bad
	msg == "K1: EL-Openglo: --el-view missing"
}

test_k2_refuses_a_foreign_property if {
	foreign := object.union(block, {"--el-made-up": "red"})
	bad := object.union(good, {"root": foreign, "cases": [{"id": "EL-Openglo", "expected": exp, "got": foreign}, good.cases[1]]})
	some msg in p.deny with input as bad
	msg == "K2: EL-Openglo: --el-made-up is not a token"
}

test_k3_refuses_a_seen_ghost_without_color_mix if {
	nomix := object.union(block, {"--el-fg-in-seen": "var(--el-fg-in)"})
	bad := object.union(good, {"root": nomix, "cases": [{"id": "EL-Openglo", "expected": exp, "got": nomix}, good.cases[1]]})
	some msg in p.deny with input as bad
	msg == "K3: EL-Openglo: --el-fg-in-seen is not color-mix(fg_in over view)"
}

test_k4_refuses_a_light_scheme_that_is_not_lit if {
	some msg in p.deny with input as object.union(good, {"light": object.union(lit, {"--el-fg": "rgb(1 2 3)"})})
	msg == "K4: prefers-color-scheme: light is not EL-Openglo-Lit"
}

# a null parsed is not a parsed sheet: a stale sheet is neither judged nor admitted
test_null_parsed_does_not_fire if {
	stale := object.union(block, {"--el-fg": "rgb(0 0 0)"})
	bad := object.union(good, {"parsed": null, "root": stale, "cases": [{"id": "EL-Openglo", "expected": exp, "got": stale}, good.cases[1]]})
	count(p.deny) == 0 with input as bad
	count(p.admitted) == 0 with input as bad
}

test_tinycss2_absent_is_withheld if {
	skip := object.union(good, {"parsed": false})
	count(p.deny) == 0 with input as skip
	count(p.withheld) == 1 with input as skip
}
