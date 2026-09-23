# A refusing and an admitting case per rule. The refusing fixture for L1/L5 is
# the DEAD ROTATION as the harness measured it on 2026-09-22 (text on the
# board, x parked, running never true again); for L3 a replace that tore.
package el.marquee_live_test

import data.el.marquee_live as ml
import rego.v1

# a clean two-rotation trace: arrive, scroll off, expire mid-run, finish, drain, arrive again, wake
clean := {"runner": true, "width": 420, "hovered": {"samples": []}, "events": [
	{"t": 300, "op": "arrive", "id": 1, "shows": "app: hello"},
	{"t": 900, "op": "expire", "id": 1, "shows": ""},
	{"t": 1600, "op": "arrive", "id": 2, "shows": "app: two"},
], "samples": [
	{"t": 100, "text": "", "x": 421, "running": false, "count": 0},
	{"t": 300, "text": "app: hello", "x": 421, "running": false, "count": 1},
	{"t": 340, "text": "app: hello", "x": 400, "running": true, "count": 1},
	{"t": 380, "text": "app: hello", "x": 300, "running": true, "count": 1},
	{"t": 600, "text": "app: hello", "x": 100, "running": true, "count": 1},
	{"t": 880, "text": "app: hello", "x": -100, "running": true, "count": 1},
	{"t": 900, "text": "app: hello", "x": -150, "running": true, "count": 0},
	{"t": 1000, "text": "app: hello", "x": -212, "running": true, "count": 0},
	{"t": 1100, "text": "", "x": -212, "running": false, "count": 0},
	{"t": 1600, "text": "app: two", "x": -212, "running": false, "count": 1},
	{"t": 1640, "text": "app: two", "x": 414, "running": true, "count": 1},
	{"t": 1700, "text": "app: two", "x": 300, "running": true, "count": 1},
]}

test_admits_clean if {
	count(ml.deny) == 0 with input as clean
	count(ml.withheld) == 0 with input as clean
}

test_l0_refuses_no_samples if {
	some msg in ml.deny with input as object.union(clean, {"samples": []})
	startswith(msg, "L0:")
}

# the dead rotation: text on the board, never running
dead := object.union(clean, {"samples": [
	{"t": 300, "text": "app: hello", "x": 421, "running": false, "count": 1},
	{"t": 340, "text": "app: hello", "x": 421, "running": false, "count": 1},
	{"t": 380, "text": "app: hello", "x": 421, "running": false, "count": 1},
	{"t": 1600, "text": "app: hello", "x": 421, "running": false, "count": 2},
	{"t": 1640, "text": "app: hello", "x": 421, "running": false, "count": 2},
]})

test_l1_refuses_text_without_scrolling if {
	some msg in ml.deny with input as dead
	startswith(msg, "L1:")
}

test_l1_admits_the_deferred_start if {
	# one idle sample at the arrival, running two samples later: not a defect
	count([m | some m in ml.deny with input as clean; startswith(m, "L1:")]) == 0
}

test_l2_refuses_an_arrival_never_shown if {
	some msg in ml.deny with input as dead
	startswith(msg, "L2:")
	contains(msg, "app: two")
}

test_l3_refuses_a_tear if {
	torn := object.union(clean, {"events": [{"t": 900, "op": "replace", "id": 1, "shows": "app: new"}], "samples": [
		{"t": 880, "text": "app: hello", "x": -100, "running": true, "count": 1},
		{"t": 900, "text": "app: new", "x": -150, "running": true, "count": 1},
		{"t": 940, "text": "app: new", "x": -190, "running": true, "count": 1},
	]})
	some msg in ml.deny with input as torn
	startswith(msg, "L3:")
}

test_l3_admits_a_change_at_the_boundary if {
	count([m | some m in ml.deny with input as clean; startswith(m, "L3:")]) == 0
}

# ⚑ THE MISATTRIBUTION, AS A REGRESSION TEST. Measured 2026-09-22 on the live
# harness: L3 denied "expire of id 21 changed the board 'app: alarm • app: quiet'
# -> 'app: quiet'". Expiring 21 IS quiet, so removing it cannot leave a board
# showing quiet — the change was id 20's expiry landing correctly on the rotation
# boundary in the 100 ms gap before id 21's event. Keyed on event proximity, any
# two events closer than one rotation read as a tear; the boundary flag is what
# separates "changed near an event" from "changed off a boundary".
test_l3_admits_a_neighbours_deferral_landing_on_the_boundary if {
	neighbour := object.union(clean, {"events": [
		{"t": 13000, "op": "expire", "id": 20, "shows": ""},
		{"t": 13100, "op": "expire", "id": 21, "shows": ""},
	], "samples": [
		{"t": 12980, "text": "app: alarm     •     app: quiet", "x": -300, "running": true, "count": 2, "boundary": false},
		{"t": 13060, "text": "app: alarm     •     app: quiet", "x": 397, "running": true, "count": 1, "boundary": true},
		{"t": 13140, "text": "app: quiet", "x": 377, "running": true, "count": 1, "boundary": true},
	]})
	count([m | some m in ml.deny with input as neighbour; startswith(m, "L3:")]) == 0
}

# ⚑ AND THE BOUNDARY FLAG MUST NOT SWALLOW A REAL TEAR — otherwise the repair
# buys its silence by disarming the rule. A change off a boundary still denies
# even when a boundary exists elsewhere in the run.
test_l3_still_refuses_a_tear_when_boundaries_exist if {
	mixed := object.union(clean, {"events": [{"t": 900, "op": "replace", "id": 1, "shows": "app: new"}], "samples": [
		{"t": 860, "text": "app: hello", "x": 400, "running": true, "count": 1, "boundary": true},
		{"t": 880, "text": "app: hello", "x": -100, "running": true, "count": 1, "boundary": false},
		{"t": 900, "text": "app: new", "x": -150, "running": true, "count": 1, "boundary": false},
	]})
	some msg in ml.deny with input as mixed
	startswith(msg, "L3:")
}

test_l4_refuses_a_forward_jump if {
	jumpy := object.union(clean, {"samples": [
		{"t": 300, "text": "app: hello", "x": 300, "running": true, "count": 1},
		{"t": 340, "text": "app: hello", "x": 350, "running": true, "count": 1},
	]})
	some msg in ml.deny with input as jumpy
	startswith(msg, "L4:")
}

test_l4_admits_a_reset_to_the_right_edge if {
	reset := object.union(clean, {"samples": [
		{"t": 300, "text": "app: hello", "x": -200, "running": true, "count": 1},
		{"t": 340, "text": "app: hello", "x": 414, "running": true, "count": 1},
	]})
	count([m | some m in ml.deny with input as reset; startswith(m, "L4:")]) == 0
}

test_l5_refuses_a_board_that_does_not_wake if {
	asleep := object.union(clean, {"samples": [
		{"t": 100, "text": "", "x": -212, "running": false, "count": 0},
		{"t": 1600, "text": "app: two", "x": -212, "running": false, "count": 1},
		{"t": 1700, "text": "app: two", "x": -212, "running": false, "count": 1},
	]})
	some msg in ml.deny with input as asleep
	startswith(msg, "L5:")
}

test_l6_refuses_a_stall_that_reports_running if {
	# the hover-pause stall as measured: x parked, running true, eleven samples
	held := [{"t": 1300 + (40 * k), "text": "app: hello", "x": 7.2, "running": true, "count": 1} | some k in numbers.range(0, 11)]
	stalled := object.union(clean, {"samples": held})
	onsets := [m | some m in ml.deny with input as stalled; startswith(m, "L6:")]
	count(onsets) == 1
}

test_l6_admits_a_moving_board if {
	count([m | some m in ml.deny with input as clean; startswith(m, "L6:")]) == 0
}

# W51: the hovered run — paused, the ring breathing
hovered_ok := {"samples": [
	{"t": 1300, "text": "app: hello", "x": 7.2, "running": true, "paused": true, "ring": 0.57, "count": 1},
	{"t": 1340, "text": "app: hello", "x": 7.2, "running": true, "paused": true, "ring": 0.71, "count": 1},
	{"t": 1380, "text": "app: hello", "x": 7.2, "running": true, "paused": true, "ring": 0.86, "count": 1},
]}

test_l7_admits_a_pulsing_ring if {
	count([m | some m in ml.deny with input as object.union(clean, {"hovered": hovered_ok}); startswith(m, "L7:")]) == 0
}

test_l7_refuses_a_ring_that_does_not_pulse if {
	flat := {"samples": [
		{"t": 1300, "text": "app: hello", "x": 7.2, "running": true, "paused": true, "ring": 0.57, "count": 1},
		{"t": 1340, "text": "app: hello", "x": 7.2, "running": true, "paused": true, "ring": 0.57, "count": 1},
	]}
	some msg in ml.deny with input as object.union(clean, {"hovered": flat})
	contains(msg, "did not pulse")
}

test_l7_refuses_a_dark_ring_while_paused if {
	dark := {"samples": [
		{"t": 1300, "text": "app: hello", "x": 7.2, "running": true, "paused": true, "ring": 0, "count": 1},
		{"t": 1340, "text": "app: hello", "x": 7.2, "running": true, "paused": true, "ring": 0.5, "count": 1},
	]}
	some msg in ml.deny with input as object.union(clean, {"hovered": dark})
	contains(msg, "ring dark")
}

test_l7_refuses_a_lit_ring_while_not_paused if {
	lit := object.union(clean, {"samples": [{"t": 300, "text": "app: hello", "x": 300, "running": true, "paused": false, "ring": 0.6, "count": 1}]})
	some msg in ml.deny with input as lit
	contains(msg, "ring is lit")
}

# W35: the bound colours under the variant's scheme
bound_ok := object.union(clean, {"variant": "EL-Amber", "expected": {"lit": "#ffd499", "ghost": "#e5bf89", "ground": "#140f08"},
	"samples": [
		{"t": 100, "text": "", "x": 421, "running": false, "count": 0, "lit": "#000000", "ghost": "#000000", "ground": "#000000"},
		{"t": 500, "text": "app: hello", "x": 300, "running": true, "count": 1, "lit": "#ffd499", "ghost": "#e5bf89", "ground": "#140f08"},
		{"t": 540, "text": "app: hello", "x": 280, "running": true, "count": 1, "lit": "#ffd499", "ghost": "#e5bf89", "ground": "#140f08"},
	]})

test_l8_admits_the_variant_tokens_after_settling if {
	count([m | some m in ml.deny with input as bound_ok; startswith(m, "L8:")]) == 0
}

test_l8_refuses_a_colour_off_the_variant if {
	off := object.union(bound_ok, {"samples": [
		{"t": 500, "text": "app: hello", "x": 300, "running": true, "count": 1, "lit": "#99ffeb", "ghost": "#e5bf89", "ground": "#140f08"},
		{"t": 540, "text": "app: hello", "x": 280, "running": true, "count": 1, "lit": "#99ffeb", "ghost": "#e5bf89", "ground": "#140f08"},
	]})
	msgs := [m | some m in ml.deny with input as off; startswith(m, "L8:")]
	count(msgs) == 1
	contains(msgs[0], "lit is #99ffeb")
}

# W46: a critical arrival is painted in the hot token
hot_ok := object.union(clean, {"events": [
	{"t": 300, "op": "arrive", "id": 20, "fields": {"urgency": 2}, "shows": "app: alarm"},
], "samples": [
	{"t": 500, "text": "app: alarm", "painted": "app: alarm", "x": 300, "running": true, "count": 1, "lit": "#ffd499", "hot": "#ffb000", "ink": ["#ffb000"]},
	{"t": 540, "text": "app: alarm", "painted": "app: alarm", "x": 280, "running": true, "count": 1, "lit": "#ffd499", "hot": "#ffb000", "ink": ["#ffb000"]},
]})

test_l9_admits_a_critical_in_the_hot_token if {
	count([m | some m in ml.deny with input as hot_ok; startswith(m, "L9:")]) == 0
}

test_l9_refuses_a_critical_in_the_lit_token if {
	off := object.union(hot_ok, {"samples": [
		{"t": 500, "text": "app: alarm", "painted": "app: alarm", "x": 300, "running": true, "count": 1, "lit": "#ffd499", "hot": "#ffb000", "ink": ["#ffd499"]},
	]})
	some msg in ml.deny with input as off
	startswith(msg, "L9:")
}

test_l9_tolerates_the_paint_lag if {
	# the swap's first sample: the new text, the previous paint's inks — not judged
	lag := object.union(hot_ok, {"samples": [
		{"t": 500, "text": "app: alarm", "painted": "app: hello", "x": 300, "running": true, "count": 1, "lit": "#ffd499", "hot": "#ffb000", "ink": ["#ffd499"]},
		{"t": 540, "text": "app: alarm", "painted": "app: alarm", "x": 280, "running": true, "count": 1, "lit": "#ffd499", "hot": "#ffb000", "ink": ["#ffb000"]},
	]})
	count([m | some m in ml.deny with input as lag; startswith(m, "L9:")]) == 0
}

test_l9_refuses_a_critical_that_never_shows if {
	off := object.union(hot_ok, {"samples": [
		{"t": 500, "text": "app: other", "painted": "app: other", "x": 300, "running": true, "count": 1, "lit": "#ffd499", "hot": "#ffb000", "ink": ["#ffd499"]},
	]})
	some msg in ml.deny with input as off
	contains(msg, "never reached the board")
}

test_l9_refuses_a_hot_token_equal_to_lit if {
	off := object.union(hot_ok, {"samples": [
		{"t": 500, "text": "app: alarm", "painted": "app: alarm", "x": 300, "running": true, "count": 1, "lit": "#ffd499", "hot": "#ffd499", "ink": ["#ffd499"]},
	]})
	some msg in ml.deny with input as off
	contains(msg, "invisible")
}

# W46: a tap on an action run reaches invokeAction
tapped_ok := object.union(clean, {"events": [
	{"t": 300, "op": "arrive", "id": 30, "fields": {"actionNames": ["open"]}, "shows": "app: act [Open]"},
	{"t": 600, "op": "tap", "id": 30, "fields": {"text": "[Open]"}, "shows": "app: act [Open]"},
], "samples": [
	{"t": 500, "text": "app: act [Open]", "painted": "app: act [Open]", "x": 300, "running": true, "count": 1, "tap": null, "invoked": []},
	{"t": 640, "text": "app: act [Open]", "painted": "app: act [Open]", "x": 280, "running": true, "count": 1,
		"tap": {"index": 9, "kind": "action", "action": "open", "item": 30, "row": 0}, "invoked": [{"row": 0, "action": "open"}]},
]})

test_l10_admits_a_tap_that_invoked if {
	count([m | some m in ml.deny with input as tapped_ok; startswith(m, "L10:")]) == 0
}

test_l10_refuses_a_tap_that_resolved_to_nothing if {
	off := object.union(tapped_ok, {"samples": [
		{"t": 640, "text": "app: act [Open]", "painted": "app: act [Open]", "x": 280, "running": true, "count": 1,
			"tap": {"index": 3, "kind": "none"}, "invoked": []},
	]})
	some msg in ml.deny with input as off
	startswith(msg, "L10:")
}

# W46 jobs: a gauge with one column per distinct percentage
job_ok := object.union(clean, {"events": [
	{"t": 300, "op": "arrive", "id": 40, "fields": {"type": 2, "percentage": 10}, "shows": "kio: copying"},
	{"t": 500, "op": "replace", "id": 40, "fields": {"type": 2, "percentage": 50}, "shows": "kio: copying"},
	{"t": 700, "op": "replace", "id": 40, "fields": {"type": 2, "percentage": 90}, "shows": "kio: copying"},
], "samples": [
	{"t": 400, "text": "kio: copying ░", "painted": "kio: copying ░", "x": 300, "running": true, "count": 1, "series": [[1]]},
	{"t": 900, "text": "kio: copying ░", "painted": "kio: copying ░", "x": 200, "running": true, "count": 1, "series": [[1, 4, 7]]},
]})

test_l11_admits_a_three_column_gauge if {
	count([m | some m in ml.deny with input as job_ok; startswith(m, "L11:")]) == 0
}

test_l11_refuses_a_gauge_that_never_grew if {
	off := object.union(job_ok, {"samples": [
		{"t": 900, "text": "kio: copying ░", "painted": "kio: copying ░", "x": 200, "running": true, "count": 1, "series": [[1]]},
	]})
	some msg in ml.deny with input as off
	startswith(msg, "L11:")
}

test_l11_refuses_a_falling_gauge_for_rising_progress if {
	off := object.union(job_ok, {"samples": [
		{"t": 900, "text": "kio: copying ░", "painted": "kio: copying ░", "x": 200, "running": true, "count": 1, "series": [[7, 4, 1]]},
	]})
	some msg in ml.deny with input as off
	startswith(msg, "L11:")
}

# null is truthy to a bare Rego reference: a null runner has not run, so L0 stays silent
test_null_runner_does_not_fire if {
	inp := {"runner": null, "events": [], "samples": [], "width": 0, "hovered": {"samples": []}}
	count([m | some m in ml.deny with input as inp; startswith(m, "L0:")]) == 0
}

# a null `running` is not running: no forward jump (L4) and no running stall (L6)
test_null_running_does_not_fire if {
	jumpy := object.union(clean, {"samples": [
		{"t": 300, "text": "app: hello", "x": 300, "running": null, "count": 1},
		{"t": 340, "text": "app: hello", "x": 350, "running": null, "count": 1},
	]})
	count([m | some m in ml.deny with input as jumpy; startswith(m, "L4:")]) == 0
	held := [{"t": 1300 + (40 * k), "text": "app: hello", "x": 7.2, "running": null, "count": 1} | some k in numbers.range(0, 11)]
	count([m | some m in ml.deny with input as object.union(clean, {"samples": held}); startswith(m, "L6:")]) == 0
}

# a null `paused` is not paused: a dark, flat ring is then not an L7 defect
test_null_paused_does_not_fire if {
	unstated := {"samples": [
		{"t": 1300, "text": "app: hello", "x": 7.2, "running": true, "paused": null, "ring": 0, "count": 1},
		{"t": 1340, "text": "app: hello", "x": 7.2, "running": true, "paused": null, "ring": 0, "count": 1},
	]}
	count([m | some m in ml.deny with input as object.union(clean, {"hovered": unstated}); startswith(m, "L7:")]) == 0
}

# exactly-once: a sample whose judged fields are all null is withheld, never judged
test_all_null_case_withheld_only if {
	blank := {"t": 300, "text": "app: hello", "x": 421, "running": null, "paused": null, "boundary": null, "ring": 0.6, "count": 1}
	inp := object.union(clean, {"samples": [blank, blank, blank]})
	w := ml.withheld with input as inp
	"W: main sample t=300: running was not measured" in w
	"W: main sample t=300: paused was not measured" in w
	"W: main sample t=300: boundary was not measured" in w
	d := ml.deny with input as inp
	count([m | some m in d; regex.match(`^L[1347]:`, m)]) == 0
}

# population flag: a null or absent runner is withheld (N1 `not input.runner`)
test_null_runner_is_withheld if {
	inp := {"runner": null, "events": [], "samples": [], "width": 0, "hovered": {"samples": []}}
	w := ml.withheld with input as inp
	"W: runner was not measured" in w
	count(ml.deny) == 0 with input as inp
	w2 := ml.withheld with input as object.remove(clean, ["runner"])
	"W: runner was not measured" in w2
}

# N1 (L1 `not s.running` / `not later.running`): the dead rotation with running
# null is not "not scrolling" — withheld
test_null_running_l1_withheld if {
	nulled := object.union(dead, {"samples": [object.union(s, {"running": null}) | some s in dead.samples]})
	count([m | some m in ml.deny with input as nulled; startswith(m, "L1:")]) == 0
	w := ml.withheld with input as nulled
	"W: main sample t=300: running was not measured" in w
}

# N1 (L3 `not a.boundary`): a null boundary is not "off the boundary"
test_null_boundary_l3_withheld if {
	torn := object.union(clean, {"events": [{"t": 900, "op": "replace", "id": 1, "shows": "app: new"}], "samples": [
		{"t": 880, "text": "app: hello", "x": -100, "running": true, "count": 1, "boundary": false},
		{"t": 900, "text": "app: new", "x": -150, "running": true, "count": 1, "boundary": null},
	]})
	count([m | some m in ml.deny with input as torn; startswith(m, "L3:")]) == 0
	w := ml.withheld with input as torn
	"W: main sample t=900: boundary was not measured" in w
}

# N1 (L5 idle_before `not s.running`): a null idle sample is not "idle"
test_null_running_idle_before_withheld if {
	asleep := object.union(clean, {"samples": [
		{"t": 100, "text": "", "x": -212, "running": null, "count": 0},
		{"t": 1600, "text": "app: two", "x": -212, "running": false, "count": 1},
		{"t": 1700, "text": "app: two", "x": -212, "running": false, "count": 1},
	]})
	count([m | some m in ml.deny with input as asleep; startswith(m, "L5:")]) == 0
	w := ml.withheld with input as asleep
	"W: main sample t=100: running was not measured" in w
}

# EXTRA: runs_after's `s.running` — a null running after the arrival is neither
# "woke" (HEAD: null is truthy, so L5 was silently satisfied) nor "did not wake"
test_null_running_runs_after_withheld if {
	unknown := object.union(clean, {"samples": [
		{"t": 100, "text": "", "x": -212, "running": false, "count": 0},
		{"t": 1600, "text": "app: two", "x": -212, "running": null, "count": 1},
		{"t": 1700, "text": "app: two", "x": -212, "running": null, "count": 1},
	]})
	count([m | some m in ml.deny with input as unknown; startswith(m, "L5:")]) == 0
	w := ml.withheld with input as unknown
	"L5: arrival of id 2 at t=1600: whether the board woke was not measured" in w
}

# N1 (L7 `not s.paused`): a null paused on the main run is not "not paused"
test_null_paused_main_l7_withheld if {
	lit := object.union(clean, {"samples": [{"t": 300, "text": "app: hello", "x": 300, "running": true, "paused": null, "ring": 0.6, "count": 1}]})
	count([m | some m in ml.deny with input as lit; contains(m, "ring is lit")]) == 0
	w := ml.withheld with input as lit
	"W: main sample t=300: paused was not measured" in w
}

test_withheld_without_runner if {
	inp := {"runner": false, "events": [], "samples": [], "width": 0, "hovered": {"samples": []}}
	count(ml.deny) == 0 with input as inp
	count(ml.withheld) == 1 with input as inp
}
