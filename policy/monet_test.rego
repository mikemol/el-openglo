package el.monet_test

import data.el.monet as p
import rego.v1

# real cases (--json, 2026-09-23)
amber := {"id": "EL-Amber", "missing": null, "dark": true, "text_on_surface": 14.346099415994113, "on_primary": 7.738847554810347, "hue_delta": 0.08061874068589248, "surface_vs_ground_dE": 2.5260887531179925}

azure_lit := {"id": "EL-Azure-Lit", "missing": null, "dark": false, "text_on_surface": 16.2710062638345, "on_primary": 6.435950168881977, "hue_delta": 0.6692825096613433, "surface_vs_ground_dE": 21.456966212448105}

good := {"library": true, "roster": ["EL-Amber", "EL-Azure-Lit"], "cases": [amber, azure_lit]}

bent(edit) := object.union(good, {"cases": [object.union(amber, edit), azure_lit]})

# ⚑ the Lit variant's surface is 21.5 dE from ground and is ADMITTED — the policy
# claims surface agreement only on the dark schemes (android.md's recorded disagreement)
test_admits_the_real_derivation if {
	count(p.deny) == 0 with input as good
	p.admitted == {"EL-Amber", "EL-Azure-Lit"} with input as good
}

test_m0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "M0: no variants were measured")
}

test_m0_withholds_an_absent_library if {
	w := {"library": false, "roster": ["EL-Amber"], "cases": []}
	count(p.deny) == 0 with input as w
	some msg in p.withheld with input as w
	msg == "M0: material-color-utilities is not installed here (uv sync --extra research); 0 of 1 variants measured"
}

# the real failure (W65, probe monet/typed-variants): a typed list dropped a
# variant and "6 of 6" became "5 of 5", exit 0
test_m0_refuses_a_declared_variant_not_measured if {
	some msg in p.deny with input as object.union(good, {"cases": [amber]})
	msg == "M0: EL-Azure-Lit: declared but not measured"
}

test_m0_refuses_an_unmeasurable_variant if {
	some msg in p.deny with input as object.union(good, {"cases": [amber, {"id": "EL-Azure-Lit", "missing": "compare() returned no measurement"}]})
	msg == "M0: EL-Azure-Lit: compare() returned no measurement"
}

test_m1_refuses_a_text_pair_below_aa if {
	some msg in p.deny with input as bent({"text_on_surface": 1})
	msg == "M1: EL-Amber: Monet on_surface/surface 1.00 < 4.5"
}

test_m1_refuses_an_on_primary_below_aa if {
	some msg in p.deny with input as bent({"on_primary": 4.49})
	msg == "M1: EL-Amber: Monet on_primary/primary 4.49 < 4.5"
}

# the docstring's first-run finding: a 31.9 dE primary drift passed a dE arm; the
# hue arm is what replaced it. Here, an amber-seeded primary on a teal seed.
test_m2_refuses_a_foreign_hue if {
	some msg in p.deny with input as bent({"hue_delta": 102.3})
	msg == "M2: EL-Amber: Monet primary hue drifted 102.3° from the seed (> 12.0)"
}

test_m3_refuses_a_dark_surface_far_from_ground if {
	some msg in p.deny with input as bent({"surface_vs_ground_dE": 21.46})
	msg == "M3: EL-Amber: Monet dark surface is 21.5 dE from ground (> 5.0)"
}

test_m0_refuses_a_null_quantity if {
	some msg in p.deny with input as bent({"hue_delta": null})
	msg == "M0: EL-Amber: a quantity was not measured"
}
