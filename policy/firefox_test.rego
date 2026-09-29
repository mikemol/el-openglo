package el.firefox_test

import data.el.firefox as p
import rego.v1

case := {
	"id": "EL-Openglo", "parse_error": null, "missing_required": [], "wrong_colours": [],
	"unmapped_keys": [], "color_scheme": "dark", "want_scheme": "dark",
	"gecko_id": "el-openglo@el-openglo.theme", "lint_errors": [],
}

dyn := {
	"id": "dynamic", "missing_variants": [], "extra_variants": [], "drifted": [],
	"permissions": ["storage", "theme"], "options_page": "options.html",
	"options_page_shipped": true, "lint_errors": [],
}

good := {"roster": ["EL-Openglo"], "roster_drift": [], "cases": [case], "dynamic": dyn}

one(c) := {"roster": ["EL-Openglo"], "roster_drift": [], "cases": [c], "dynamic": dyn}

with_dyn(d) := object.union(good, {"dynamic": object.union(dyn, d)})

test_admits_a_clean_manifest if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	p.admitted == {"EL-Openglo", "dynamic"} with input as good
}

# X7 (W135): the dynamic extension carries exactly the roster, identical to the static themes
test_x7_refuses_a_missing_variant if {
	"X7: dynamic: variant EL-Amber is not in themes.json" in p.deny with input as with_dyn({"missing_variants": ["EL-Amber"]})
}

test_x7_refuses_an_extra_variant if {
	"X7: dynamic: themes.json carries EL-Nope, which the roster does not declare" in p.deny with input as with_dyn({"extra_variants": ["EL-Nope"]})
}

test_x7_refuses_drift if {
	inp := with_dyn({"drifted": ["EL-Openglo"]})
	"X7: dynamic: EL-Openglo in themes.json differs from its static theme" in p.deny with input as inp
	not "dynamic" in p.admitted with input as inp
}

# X9 (W143): an AMO-blocking lint WARNING is denied; an ordinary warning is not
test_x9_refuses_a_blocking_warning_on_a_theme if {
	inp := one(object.union(case, {"lint_warnings": ["MISSING_DATA_COLLECTION_PERMISSIONS"]}))
	"X9: EL-Openglo: web-ext warning MISSING_DATA_COLLECTION_PERMISSIONS blocks AMO submission" in p.deny with input as inp
	not "EL-Openglo" in p.admitted with input as inp
}

test_x9_refuses_a_blocking_warning_on_the_dynamic_extension if {
	inp := with_dyn({"lint_warnings": ["MISSING_DATA_COLLECTION_PERMISSIONS"]})
	"X9: dynamic: web-ext warning MISSING_DATA_COLLECTION_PERMISSIONS blocks AMO submission" in p.deny with input as inp
	not "dynamic" in p.admitted with input as inp
}

test_x9_admits_an_ordinary_warning if {
	inp := one(object.union(case, {"lint_warnings": ["UNSAFE_VAR_ASSIGNMENT"]}))
	count(p.deny) == 0 with input as inp
	"EL-Openglo" in p.admitted with input as inp
}

# X8: permissions and the shipped chooser
test_x8_refuses_a_missing_permission if {
	"X8: dynamic: permission \"storage\" is missing" in p.deny with input as with_dyn({"permissions": ["theme"]})
}

test_x8_refuses_an_unshipped_options_page if {
	"X8: dynamic: the options page is named but not shipped (or not named)" in p.deny with input as with_dyn({"options_page_shipped": false})
}

test_x6_dynamic_withheld_without_web_ext if {
	inp := with_dyn({"lint_errors": null})
	"X6: dynamic: web-ext is not installed here; the lint is unmeasured" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
}

test_dynamic_unmeasured_is_withheld if {
	inp := {"roster": ["EL-Openglo"], "roster_drift": [], "cases": [case]}
	"W: dynamic: the dynamic extension was not measured" in p.withheld with input as inp
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
	not "EL-Openglo" in p.admitted with input as one(c)
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
	p.admitted == {"EL-Openglo", "dynamic"} with input as inp
}

# exactly-once: a parsed manifest whose facts are null is withheld, never judged
test_all_null_case_withheld_only if {
	c := {"id": "EL-Openglo", "parse_error": null, "missing_required": null, "wrong_colours": null, "unmapped_keys": null, "color_scheme": null, "want_scheme": null, "gecko_id": null, "lint_errors": null}
	w := p.withheld with input as one(c)
	"W: EL-Openglo: missing_required was not measured" in w
	"W: EL-Openglo: gecko_id was not measured" in w
	count(p.deny) == 0 with input as one(c)
	not "EL-Openglo" in p.admitted with input as one(c)
}

test_denial_does_not_leak_across_prefixed_ids if {
	lit := object.union(case, {"id": "EL-Openglo-Lit", "want_scheme": "light", "gecko_id": "el-openglo-lit@x"})
	inp := {"roster": ["EL-Openglo", "EL-Openglo-Lit"], "roster_drift": [], "cases": [case, lit]}
	p.admitted == {"EL-Openglo"} with input as inp
}
