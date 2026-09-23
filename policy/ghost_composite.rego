# METADATA
# title: "C0 — no variants measured admits nothing"
# description: |
#   The measurement is `scripts/check_ghost_composite.py --json [--mode M]`: the
#   parsing mode (looked_at / glanced_at), the solved alpha, the readability
#   ceiling (cvd_gate.GHOST_READABLE_LC), the ghostAlpha the EMITTED
#   SegmentChar.qml carries (looked-at only), and per variant the ghost's
#   declared and COMPOSITED (source-over at alpha) WCAG ratio and |Lc| against
#   its APCA floor. The contrast the colour gates measure and the contrast that
#   renders are different quantities; this is the join. Weakness: a flat alpha
#   over the unlit core — the lit bloom underlay and the matrix dot field
#   (--matrix) are not modelled here.
package el.ghost_composite

import data.el.fmt
import rego.v1

# how far under the ceiling a looked-at seen ghost may sit and still be ON
# TARGET: derive_ghost_through_alpha's 8-bit stepping lands 0.1-0.4 Lc under; a
# whole Lc is the widest that stepping can cost. Azure's 5.0 (W23) is not that.
target_slack := 1.0

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "C0: no variants were measured; the grid is not built, not the ghost visible"
}

# METADATA
# title: "C1 — the seen ghost clears its floor"
deny contains msg if {
	some c in input.cases
	c.lc_composited < c.floor_lc
	msg := sprintf("C1: %s: the ghost renders at Lc %v against a floor of Lc %v (declared Lc %v, drawn at alpha %v)", [c.id, d1(c.lc_composited), d1(c.floor_lc), d1(c.lc_declared), input.alpha])
}

# METADATA
# title: "C2 — the seen ghost stays under the readability ceiling (texture, not text)"
deny contains msg if {
	some c in input.cases
	c.lc_composited >= input.ceiling
	msg := sprintf("C2: %s: the composited ghost reads at Lc %v, at or over the %v ceiling", [c.id, d1(c.lc_composited), input.ceiling])
}

# METADATA
# title: "C3 — looked-at: the seen ghost is ON TARGET, not merely inside the band (W23)"
deny contains msg if {
	input.mode == "looked_at"
	some c in input.cases
	c.lc_composited < input.ceiling - target_slack
	msg := sprintf("C3: %s: the seen ghost sits at Lc %v, more than %v under the %v ceiling it is solved toward (W23)", [c.id, d1(c.lc_composited), target_slack, input.ceiling])
}

# one decimal: sprintf's %.1f renders an integral JSON number (25.0 arrives as
# 25) as "%!f(int=25)"; data.el.fmt (policy/lib/fmt.rego) is the one fix for
# every policy, and prints 25 as "25.0"
d1(x) := fmt.fixed(x, 1)

# METADATA
# title: "C4 — looked-at: the emitted SegmentChar.qml draws the solved alpha"
deny contains msg if {
	input.mode == "looked_at"
	count(object.get(input, "cases", [])) > 0
	not alpha_carried
	msg := sprintf("C4: the emitted SegmentChar.qml carries ghostAlpha=%v, not the solved %v; the gate measured an alpha the screen does not draw", [object.get(input, "rendered_alpha", null), input.alpha])
}

alpha_carried if {
	input.rendered_alpha != null
	abs(input.rendered_alpha - input.alpha) <= 1e-9
}

admitted contains c.id if {
	some c in input.cases
	c.lc_composited >= c.floor_lc
	c.lc_composited < input.ceiling
	on_target(c)
}

on_target(c) if input.mode != "looked_at"

on_target(c) if {
	input.mode == "looked_at"
	c.lc_composited >= input.ceiling - target_slack
}
