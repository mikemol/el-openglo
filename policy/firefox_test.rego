package el.firefox_test

import data.el.firefox as p
import rego.v1

case := {
	"id": "EL-Openglo", "parse_error": null, "missing_required": [], "wrong_colours": [],
	"unmapped_keys": [], "color_scheme": "dark", "want_scheme": "dark",
	"gecko_id": "el-openglo@el-openglo.theme", "lint_errors": [],
}

good := {"roster": ["EL-Openglo"], "roster_drift": [], "cases": [case]}

one(c) := {"roster": ["EL-Openglo"], "roster_drift": [], "cases": [c]}

test_admits_a_clean_manifest if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	p.admitted == {"EL-Openglo"} with input as good
}

test_x0_refuses_an_absent_population if {
	some m in p.deny with input as {}
	startswith(m, "X0: no manifests")
}

test_x0_refuses_emitter_drift if {
	inp := object.union(good, {"roster_drift": [{"variant": "EL-Amber", "why": "in GRID, not in make_firefox.VARIANTS"}]})
	"X0: EL-Amber: in GRID, not in make_firefox.VARIANTS" in p.deny with input as inp
}

test_x1_refuses_unparsable_json_and_admits_nothing if {
	c := object.union(case, {"parse_error": "Expecting value: line 1", "missing_required": null, "wrong_colours": null, "unmapped_keys": null, "color_scheme": null, "gecko_id": null, "lint_errors": null})
	"X1: EL-Openglo: manifest.json does not parse: Expecting value: line 1" in p.deny with input as one(c)
	count(p.admitted) == 0 with input as one(c)
	count(p.withheld) == 0 with input as one(c)
}

test_x2_refuses_a_missing_frame if {
	"X2: EL-Openglo: required colour key(s) absent: [\"frame\"]" in p.deny with input as one(object.union(case, {"missing_required": ["frame"]}))
}

test_x3_refuses_an_authored_colour if {
	w := {"key": "toolbar", "role": "bg", "got": [1, 2, 3], "want": [9, 9, 9]}
	some m in p.deny with input as one(object.union(case, {"wrong_colours": [w]}))
	startswith(m, "X3: EL-Openglo: toolbar = [1, 2, 3], not its role bg")
}

test_x3_refuses_an_unmapped_key if {
	"X3: EL-Openglo: colour key(s) no palette role maps: [\"accentcolor\"]" in p.deny with input as one(object.union(case, {"unmapped_keys": ["accentcolor"]}))
}

test_x4_refuses_the_wrong_polarity if {
	"X4: EL-Openglo: color_scheme is light, the variant's polarity wants dark" in p.deny with input as one(object.union(case, {"color_scheme": "light"}))
}

test_x5_refuses_an_id_not_naming_the_variant if {
	some m in p.deny with input as one(object.union(case, {"gecko_id": "theme@example.org"}))
	startswith(m, "X5: EL-Openglo: gecko id")
}

test_x5_refuses_an_empty_id if {
	some m in p.deny with input as one(object.union(case, {"gecko_id": ""}))
	startswith(m, "X5:")
}

test_x6_refuses_a_lint_error if {
	"X6: EL-Openglo: web-ext: MANIFEST_FIELD_INVALID" in p.deny with input as one(object.union(case, {"lint_errors": ["MANIFEST_FIELD_INVALID"]}))
}

# web-ext absent: withheld beside admitted — a SKIP, counted, not a pass of the lint
test_x6_withholds_the_lint_without_web_ext if {
	inp := one(object.union(case, {"lint_errors": null}))
	"X6: EL-Openglo: web-ext is not installed here; the lint is unmeasured" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
	p.admitted == {"EL-Openglo"} with input as inp
}

# exactly-once: a parsed manifest whose facts are null is withheld, never judged
test_all_null_case_withheld_only if {
	c := {"id": "EL-Openglo", "parse_error": null, "missing_required": null, "wrong_colours": null, "unmapped_keys": null, "color_scheme": null, "want_scheme": null, "gecko_id": null, "lint_errors": null}
	w := p.withheld with input as one(c)
	"W: EL-Openglo: missing_required was not measured" in w
	"W: EL-Openglo: gecko_id was not measured" in w
	count(p.deny) == 0 with input as one(c)
	count(p.admitted) == 0 with input as one(c)
}

test_denial_does_not_leak_across_prefixed_ids if {
	lit := object.union(case, {"id": "EL-Openglo-Lit", "want_scheme": "light", "gecko_id": "el-openglo-lit@x"})
	inp := {"roster": ["EL-Openglo", "EL-Openglo-Lit"], "roster_drift": [], "cases": [case, lit]}
	p.admitted == {"EL-Openglo"} with input as inp
}
