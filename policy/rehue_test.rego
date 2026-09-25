package el.rehue_test

import data.el.rehue as p
import rego.v1

acc := {"hue": 60, "accepted": true, "is_fg": false, "lc": 72.4, "sep": 1.8}

rej := {"hue": 240, "accepted": false, "is_fg": true, "lc": 64.1, "sep": 2.2}

case := {"id": "EL-Azure", "floor": 60, "fg_lc": 64.1, "buckets": [acc, rej]}

good := {"roster": ["EL-Azure"], "cases": [case]}

with_bucket(b) := {"roster": ["EL-Azure"], "cases": [object.union(case, {"buckets": [b, rej]})]}

test_admits_a_gated_table if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	p.admitted == {"EL-Azure"} with input as good
}

test_h0_refuses_an_absent_population if {
	"H0: no variants were measured; the roster is empty, not the hues gated" in p.deny with input as {}
}

test_h0_refuses_an_unmeasured_declared_variant if {
	"H0: EL-Amber: declared but not measured" in p.deny with input as object.union(good, {"roster": ["EL-Azure", "EL-Amber"]})
}

test_h1_refuses_fg_under_the_floor if {
	inp := {"roster": ["EL-Azure"], "cases": [object.union(case, {"fg_lc": 42.0})]}
	"H1: EL-Azure: fg itself is under the lit floor (Lc 42.0 < 60.0)" in p.deny with input as inp
	count(p.admitted) == 0 with input as inp
}

test_h2_refuses_an_accepted_hue_under_the_floor if {
	some m in p.deny with input as with_bucket(object.union(acc, {"lc": 12.5}))
	startswith(m, "H2: EL-Azure: hue 60 accepted under the lit floor")
}

test_h3_refuses_an_accepted_hue_the_ghost_hides if {
	some m in p.deny with input as with_bucket(object.union(acc, {"sep": 0.4}))
	startswith(m, "H3: EL-Azure: hue 60 accepted but not separable")
}

test_h4_refuses_a_fallback_that_is_not_fg if {
	some m in p.deny with input as with_bucket(object.union(rej, {"hue": 300, "is_fg": false}))
	m == "H4: EL-Azure: hue 300 was rejected but did not fall back to fg"
}

test_h5_refuses_a_dead_read if {
	inp := {"roster": ["EL-Azure"], "cases": [object.union(case, {"buckets": [rej]})]}
	"H5: EL-Azure: every hue falls back — the read is dead" in p.deny with input as inp
}

test_h5_refuses_no_buckets if {
	inp := {"roster": ["EL-Azure"], "cases": [object.union(case, {"buckets": []})]}
	"H5: EL-Azure: no hue buckets were measured" in p.deny with input as inp
}

# exactly-once: a null field is withheld, never denied and never admitted
test_all_null_case_withheld_only if {
	b := {"hue": 60, "accepted": null, "is_fg": null, "lc": null, "sep": null}
	inp := {"roster": ["EL-Azure"], "cases": [{"id": "EL-Azure", "floor": null, "fg_lc": null, "buckets": [b]}]}
	w := p.withheld with input as inp
	"W: EL-Azure: fg_lc was not measured" in w
	"W: EL-Azure: bucket 60 accepted was not measured" in w
	"W: EL-Azure: bucket 60 sep was not measured" in w
	count(p.deny) == 0 with input as inp
	count(p.admitted) == 0 with input as inp
}

# a variant id that is a prefix of another is not denied by the other's message
test_denial_does_not_leak_across_prefixed_ids if {
	lit := object.union(case, {"id": "EL-Azure-Lit", "fg_lc": 42.0})
	inp := {"roster": ["EL-Azure", "EL-Azure-Lit"], "cases": [case, lit]}
	p.admitted == {"EL-Azure"} with input as inp
}
