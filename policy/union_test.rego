package el.union_test

import data.el.union as p
import rego.v1

# a trimmed real case (--json, 2026-09-23: EL-Amber, two of its overrides)
amber := {
	"id": "EL-Amber", "parse_errors": 0,
	"overrides": [
		{"name": "--card-hover-color", "numbers": [0.353]},
		{"name": "--indicator-color", "numbers": [0.437]},
	],
	"solved": [
		{"var": "--indicator-color", "alpha": 0.437},
		{"var": "--card-hover-color", "alpha": 0.353},
	],
}

good := {"roster": ["EL-Amber"], "breeze": ["--card-hover-color", "--indicator-color"], "roster_drift": [], "cases": [amber]}

bent(edit) := object.union(good, {"cases": [object.union(amber, edit)]})

test_admits_solved_overrides_breeze_reads if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	p.admitted == {"EL-Amber"} with input as good
}

test_u0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "U0: no styles were measured")
}

# the real failure (W61 R1): the population was make_union.VARIANTS, so an
# emitter that dropped a variant shrank the population instead of failing
test_u0_refuses_an_emitter_that_drops_a_variant if {
	bad := object.union(good, {"roster_drift": [{"variant": "EL-Amber", "who": "make_union", "why": "make_union.VARIANTS does not declare it (GRID does)"}]})
	some msg in p.deny with input as bad
	msg == "U0: EL-Amber: make_union.VARIANTS does not declare it (GRID does)"
}

# no real U1-U3 denial is recorded; each is the defect the selftest plants
test_u1_refuses_a_malformed_sheet if {
	some msg in p.deny with input as bent({"parse_errors": 2})
	msg == "U1: EL-Amber: 2 parse error(s)"
}

test_u1_withholds_without_tinycss2 if {
	w := bent({"parse_errors": null})
	count(p.deny) == 0 with input as w
	some msg in p.withheld with input as w
	startswith(msg, "U1: EL-Amber: tinycss2")
	count(p.admitted) == 0 with input as w
}

test_u2_refuses_a_name_breeze_does_not_define if {
	some msg in p.deny with input as bent({"overrides": [
		{"name": "--card-hover-color", "numbers": [0.353]},
		{"name": "--indicator-colour", "numbers": [0.437]},
	]})
	msg == "U2: EL-Amber: overrides Breeze does not define: [\"--indicator-colour\"]"
}

test_u2_withholds_an_absent_breeze if {
	w := object.union(good, {"breeze": null})
	count(p.deny) == 0 with input as w
	some msg in p.withheld with input as w
	startswith(msg, "U2: Breeze's variables.css is absent")
	p.admitted == {"EL-Amber"} with input as w
}

test_u3_refuses_an_authored_alpha if {
	some msg in p.deny with input as bent({"overrides": [
		{"name": "--card-hover-color", "numbers": [0.353]},
		{"name": "--indicator-color", "numbers": [0.4]},
	]})
	msg == "U3: EL-Amber: --indicator-color emits [0.4], not the solved 0.437"
}

test_u3_refuses_a_solved_alpha_not_overridden if {
	some msg in p.deny with input as bent({"overrides": [{"name": "--card-hover-color", "numbers": [0.353]}]})
	msg == "U3: EL-Amber: --indicator-color is solved (0.437) but not overridden"
}

test_u4_refuses_an_alpha_outside_the_unit_interval if {
	bad := bent({"overrides": [{"name": "--card-hover-color", "numbers": [0.353]}, {"name": "--indicator-color", "numbers": [1.2]}], "solved": [{"var": "--indicator-color", "alpha": 1.2}]})
	some msg in p.deny with input as bad
	msg == "U4: EL-Amber: --indicator-color solved to 1.200, outside 0..1"
}

test_u3_ignores_an_unsolved_variable if {
	ok := bent({"solved": [{"var": "--indicator-color", "alpha": 0.437}, {"var": "--focus-color", "alpha": null}]})
	count(p.deny) == 0 with input as ok
	p.admitted == {"EL-Amber"} with input as ok
}
