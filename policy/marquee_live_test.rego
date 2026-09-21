# A refusing and an admitting case per rule. The refusing fixture for L1/L5 is
# the DEAD ROTATION as the harness measured it on 2026-09-22 (text on the
# board, x parked, running never true again); for L3 a replace that tore.
package el.marquee_live_test

import data.el.marquee_live as ml
import rego.v1

# a clean two-rotation trace: arrive, scroll off, expire mid-run, finish, drain, arrive again, wake
clean := {"runner": true, "width": 420, "events": [
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

test_withheld_without_runner if {
	inp := {"runner": false, "events": [], "samples": [], "width": 0}
	count(ml.deny) == 0 with input as inp
	count(ml.withheld) == 1 with input as inp
}
