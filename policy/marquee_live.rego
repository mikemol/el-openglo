# METADATA
# title: "L0 — an empty trace admits nothing"
# description: |
#   The measurement is `scripts/check_marquee_live.py --json`: the whole
#   marquee run headless against a stubbed notification model, driven on a
#   timeline (events, each with the text the board must then show) and sampled
#   every 40 ms (text, x, running, count). No samples means the widget did not
#   run, not that it behaved.
package el.marquee_live

import rego.v1

deny contains msg if {
	input.runner
	count(input.samples) == 0
	msg := "L0: no samples; the widget did not run"
}

deny contains msg if {
	input.runner
	count(input.events) == 0
	msg := "L0: no events; nothing drove the board"
}

# METADATA
# title: "L1 — a board that shows text is scrolling"
# description: |
#   The dead-rotation defect (COTYPE s98) and the stalled-run defects (s101):
#   text on the board with the animation not running. A run starts from a
#   deferred call, so the sample at the arrival itself may still be idle; two
#   samples later it must be running. Derived from the samples alone.
deny contains msg if {
	some i
	s := input.samples[i]
	s.text != ""
	not s.running
	later := input.samples[i + 2]
	later.text != ""
	not later.running
	msg := sprintf("L1: at t=%v the board shows %q and is not scrolling (still not at t=%v)", [s.t, s.text, later.t])
}

# METADATA
# title: "L2 — every arrival and every replace is shown"
# description: |
#   For each event that names a text, some later sample shows exactly it. A
#   notification that "just vanished" before its rotation, or a replace whose
#   new text never reached the board, fails here.
shown_after(e) if {
	some s in input.samples
	s.t >= e.t
	s.text == e.shows
}

deny contains msg if {
	some e in input.events
	e.shows != ""
	not shown_after(e)
	msg := sprintf("L2: %s of id %v at t=%v: %q never reached the board", [e.op, e.id, e.t, e.shows])
}

# METADATA
# title: "L3 — an expiry or a replace never changes the board mid-rotation"
# description: |
#   Operator: "never vanish and never tear". The text at the first sample after
#   the event equals the text at the last sample before it — the change waits
#   for the rotation boundary.
before(e) := s if {
	some i
	s := input.samples[i]
	s.t < e.t
	not later_before(e, i)
}

later_before(e, i) if {
	some j
	j > i
	input.samples[j].t < e.t
}

after(e) := s if {
	some i
	s := input.samples[i]
	s.t >= e.t
	not earlier_after(e, i)
}

earlier_after(e, i) if {
	some j
	j < i
	input.samples[j].t >= e.t
}

deny contains msg if {
	some e in input.events
	e.op in {"expire", "replace"}
	b := before(e)
	a := after(e)
	b.text != a.text
	msg := sprintf("L3: %s of id %v at t=%v changed the board mid-rotation: %q -> %q", [e.op, e.id, e.t, b.text, a.text])
}

# METADATA
# title: "L4 — x never jumps forward mid-rotation"
# description: |
#   Between consecutive scrolling samples x only decreases, except a reset to
#   the right edge that begins the next rotation. A tear is a forward jump
#   that is not a reset.
deny contains msg if {
	some i
	a := input.samples[i]
	b := input.samples[i + 1]
	a.running
	b.running
	a.text != ""
	b.text == a.text
	b.x > a.x + 1
	b.x < input.width - 40
	msg := sprintf("L4: x jumped forward %v -> %v between t=%v and t=%v", [a.x, b.x, a.t, b.t])
}

# METADATA
# title: "L5 — a drained board wakes for the next arrival"
# description: |
#   After the board has been empty and idle, an arrival must be followed by a
#   scrolling sample. This is the live report of 2026-09-22 ("doesn't respond
#   to notifications at all"), as a rule.
idle_before(e) if {
	some s in input.samples
	s.t < e.t
	s.text == ""
	not s.running
}

runs_after(e) if {
	some s in input.samples
	s.t >= e.t
	s.running
}

deny contains msg if {
	some e in input.events
	e.op == "arrive"
	idle_before(e)
	not runs_after(e)
	msg := sprintf("L5: the board was idle and did not wake for the arrival of id %v at t=%v", [e.id, e.t])
}

# METADATA
# title: "L6 — a scrolling board moves"
# description: |
#   A PAUSED animation still reports running (measured: the hover-pause held
#   the Row at x≈7 with running true for the rest of the run, and L1 was
#   blind to it). So: while running with text on the board, x must change
#   within ten consecutive samples (~400 ms; the slowest authored pace moves
#   at least one pitch in that span).
stalled(i) if {
	a := input.samples[i]
	a.running
	a.text != ""
	every k in numbers.range(1, 10) {
		b := input.samples[i + k]
		b.running
		b.text == a.text
		b.x == a.x
	}
}

deny contains msg if {
	some i
	stalled(i)
	not stalled(i - 1) # report the onset once, not every sample of the stall
	a := input.samples[i]
	msg := sprintf("L6: the board sat at x=%v with %q from t=%v while reporting running", [a.x, a.text, a.t])
}

# METADATA
# title: "W — the qml runner is absent"
withheld contains msg if {
	not input.runner
	msg := "the qml runner is not on this host; the widget did not run"
}
