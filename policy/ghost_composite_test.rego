package el.ghost_composite_test

import data.el.ghost_composite as p
import rego.v1

row(id, lc) := {"id": id, "wcag_declared": 9.0, "wcag_composited": 4.0, "floor_lc": 25.0, "lc_declared": 60.0, "lc_composited": lc}

good := {"mode": "looked_at", "alpha": 0.566, "ceiling": 30.0, "rendered_alpha": 0.566, "cases": [row("EL-Openglo", 29.7), row("EL-Azure", 29.5)]}

test_admits_a_ghost_on_target if {
	count(p.deny) == 0 with input as good
	p.admitted == {"EL-Openglo", "EL-Azure"} with input as good
}

test_c0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "C0:")
}

# the ORIGINAL defect: SegmentChar drew at 0.45 and every variant rendered ~Lc 8
test_c1_refuses_a_ghost_under_its_floor if {
	bad := object.union(good, {"cases": [row("EL-Openglo", 8.0)]})
	some msg in p.deny with input as bad
	msg == "C1: EL-Openglo: the ghost renders at Lc 8.0 against a floor of Lc 25.0 (declared Lc 60.0, drawn at alpha 0.566)"
}

# a WHOLE-NUMBER Lc (JSON 25 arrives as an int) must not print as %!f(int=25)
test_c1_message_formats_a_whole_number if {
	bad := object.union(good, {"cases": [row("EL-Openglo", 8)]})
	some msg in p.deny with input as bad
	startswith(msg, "C1:")
	not contains(msg, "%!")
}

test_c2_refuses_a_ghost_that_reads_as_text if {
	some msg in p.deny with input as object.union(good, {"cases": [row("EL-Openglo", 35.0)]})
	startswith(msg, "C2: EL-Openglo:")
}

# the real W23 failure (2026-09-21): EL-Azure's looked-at ghost at Lc 25.0 —
# inside [25, 30), passed by the band, 5 Lc short of the target
test_c3_refuses_azure_on_its_floor_not_its_target if {
	bad := object.union(good, {"cases": [row("EL-Openglo", 29.7), row("EL-Azure", 25.0)]})
	some msg in p.deny with input as bad
	msg == "C3: EL-Azure: the seen ghost sits at Lc 25.0, more than 1 under the 30 ceiling it is solved toward (W23)"
	p.admitted == {"EL-Openglo"} with input as bad
}

test_c3_glanced_mode_is_not_held_to_the_ceiling if {
	g := object.union(good, {"mode": "glanced_at", "rendered_alpha": null, "cases": [row("EL-Azure", 25.0)]})
	count(p.deny) == 0 with input as g
	p.admitted == {"EL-Azure"} with input as g
}

test_c4_refuses_a_stale_emitted_alpha if {
	some msg in p.deny with input as object.union(good, {"rendered_alpha": 0.45})
	startswith(msg, "C4: the emitted SegmentChar.qml carries ghostAlpha=0.45")
}

test_c4_refuses_a_component_with_no_ghost_alpha if {
	some msg in p.deny with input as object.union(good, {"rendered_alpha": null})
	startswith(msg, "C4:")
}

# the metric change: WCAG 1.9:1 but Lc 29.7 on a light ground — one metric, admitted
test_a_light_ground_ghost_at_lc_29_7_passes if {
	count(p.deny) == 0 with input as object.union(good, {"cases": [object.union(row("EL-Openglo-Lit", 29.7), {"wcag_composited": 1.9})]})
}
