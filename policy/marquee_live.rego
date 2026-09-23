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

import data.el.truth

deny contains msg if {
	truth.py(input.runner)
	count(input.samples) == 0
	msg := "L0: no samples; the widget did not run"
}

deny contains msg if {
	truth.py(input.runner)
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
	contains(s.text, e.shows) # a ring may carry several items; the board's text contains this one
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

	# ⚑ A CHANGE THAT LANDED ON A ROTATION BOUNDARY IS THE REQUIREMENT BEING MET,
	# not a tear — and without this clause L3 attributed one event's CORRECT
	# deferral to the next event whenever the boundary fell in the gap between
	# them. Measured 2026-09-22: "expire of id 21 changed the board 'app: alarm •
	# app: quiet' -> 'app: quiet'", where expiring 21 IS quiet, so the change was
	# id 20's expiry landing on the boundary 100 ms earlier. Any two events closer
	# together than one rotation were indistinguishable from a tear, which is why
	# this denied intermittently and under load.
	not a.boundary
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
	truth.py(a.running)
	truth.py(b.running)
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
	truth.py(s.running)
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
	truth.py(a.running)
	a.text != ""
	every k in numbers.range(1, 10) {
		b := input.samples[i + k]
		truth.py(b.running)
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
# title: "L7 — the hover-pause shows itself: the ring pulses while paused and is dark otherwise"
# description: |
#   Operator (W51): a parked pointer holds the board with no sign; the outermost
#   pips must pulse while the pause holds. Over the HOVERED run (hover-pause on,
#   the offscreen pointer at (0,0)): among the paused samples the ring opacity
#   takes more than one value and is never zero; over the main run (never
#   paused) the ring is zero at every sample. Derived from the samples.
paused_rings := {s.ring | some s in input.hovered.samples; truth.py(s.paused)}

deny contains msg if {
	truth.py(input.runner)
	count([s | some s in input.hovered.samples; truth.py(s.paused)]) > 0
	count(paused_rings) < 2
	msg := sprintf("L7: the board was paused and the ring did not pulse (opacities seen: %v)", [paused_rings])
}

deny contains msg if {
	some s in input.hovered.samples
	truth.py(s.paused)
	s.ring == 0
	msg := sprintf("L7: paused at t=%v with the ring dark", [s.t])
}

deny contains msg if {
	some s in input.samples
	not s.paused
	s.ring > 0
	msg := sprintf("L7: not paused at t=%v and the ring is lit (%v)", [s.t, s.ring])
}

# METADATA
# title: "L8 — the bound colours resolve to the variant's tokens, throughout"
# description: |
#   ⊕ONE-THEME (W35): the widget binds lit / ghost / ground to the active
#   scheme's roles, and the harness runs it under the variant's scheme with the
#   real Kirigami.Theme. After the theme settles (the first 400 ms), every
#   sample's lit / ghost / ground must equal the variant's solved fg / fg_in /
#   view. A baked hex, a wrong role or a missing colorSet fails here on the
#   RENDERED widget, not on its text.
off_token(i, k) if {
	s := input.samples[i]
	s.t >= 400
	s[k] != input.expected[k]
}

deny contains msg if {
	some i
	some k, want in input.expected
	off_token(i, k)
	not off_token(i - 1, k) # the onset, once
	s := input.samples[i]
	msg := sprintf("L8: under %s from t=%v, %s is %v, not the variant's %v", [input.variant, s.t, k, s[k], want])
}

# METADATA
# title: "L9 — a critical notification is painted in the HOT token"
# description: |
#   W46 (catalog/notify-capabilities.md): urgency 2 is painted in the hot token
#   (Kirigami.Theme.activeTextColor, fg_act) — alarm's colour, distinct from the
#   lit token that attention (the hover ring) uses. The timeline's critical
#   arrival must appear in the board's text, and every sample whose PAINTED
#   text carries it (the paint follows the swap by a turn) must list the hot
#   token among the inks that paint used; and the hot token must differ from
#   the lit token, or the alarm is invisible.
critical_shows contains s.shows if {
	some s in input.events
	s.op == "arrive"
	s.fields.urgency == 2
}

deny contains msg if {
	some shows in critical_shows
	not shows_somewhere(shows)
	msg := sprintf("L9: the critical item %q never reached the board", [shows])
}

shows_somewhere(shows) if {
	some s in input.samples
	contains(s.text, shows)
}

deny contains msg if {
	some shows in critical_shows
	some i, s in input.samples
	contains(s.painted, shows)
	s.t >= 400
	not s.hot in s.ink
	not_hot_before(i, shows)
	msg := sprintf("L9: at t=%v the board painted %q but its inks %v lack the hot token %v", [s.t, shows, s.ink, s.hot])
}

# the onset, once
not_hot_before(i, shows) if {
	i == 0
}

not_hot_before(i, shows) if {
	i > 0
	p := input.samples[i - 1]
	not contains(p.painted, shows)
}

not_hot_before(i, shows) if {
	i > 0
	p := input.samples[i - 1]
	p.hot in p.ink
}

deny contains msg if {
	some s in input.samples
	s.t >= 400
	s.hot == s.lit
	msg := sprintf("L9: the hot token equals the lit token (%v) — an alarm would be invisible", [s.hot])
}

# METADATA
# title: "L10 — a tap on an action run reaches the model's invokeAction"
# description: |
#   W46 (catalog/notify-capabilities.md): an item's actions join as " [Label]"
#   runs; a tap on one calls invokeAction(row, id) on the row that carries the
#   item. The timeline's tap events name the run's text; after each, some sample
#   must show the stub's invoked list carrying that action for that item — and
#   the widget's own lastTap must have resolved to an action, not to nothing.
tap_events contains e if {
	some e in input.events
	e.op == "tap"
}

deny contains msg if {
	some e in tap_events
	not invoked_after(e)
	msg := sprintf("L10: the tap at t=%v on %q never reached invokeAction for item %v", [e.t, e.fields.text, e.id])
}

invoked_after(e) if {
	some s in input.samples
	s.t >= e.t
	some inv in s.invoked
	s.tap.kind == "action"
	s.tap.item == e.id
	inv.action == s.tap.action
}

# METADATA
# title: "L11 — a job's progress is painted as a gauge with one column per sample"
# description: |
#   W46 (W48 folded): a Job-type item keeps its percentage history and the
#   board paints it as columns — one per distinct percentage seen, the newest at
#   the right. After the job's last progress event, some sample's painted series
#   must hold a series with exactly that many columns, each a height within the
#   matrix's rows, rising with the percentages when they rise.
job_ids contains e.id if {
	some e in input.events
	e.fields.type == 2
}

job_pcts(id) := {p | some e in input.events; e.id == id; e.fields.type == 2; p := e.fields.percentage}

last_job_t(id) := max({e.t | some e in input.events; e.id == id; e.fields.type == 2})

deny contains msg if {
	some id in job_ids
	n := count(job_pcts(id))
	not gauge_after(id, n)
	msg := sprintf("L11: job %v sent %d distinct percentages but no sample painted a %d-column gauge after t=%v", [id, n, n, last_job_t(id)])
}

gauge_after(id, n) if {
	some s in input.samples
	s.t >= last_job_t(id)
	some ser in s.series
	count(ser) == n
	every h in ser {
		h >= 0
		h <= 16
	}
	rising(ser)
}

rising(ser) if {
	not falls(ser)
}

falls(ser) if {
	some i, h in ser
	i > 0
	h < ser[i - 1]
}

# METADATA
# title: "W — the qml runner is absent"
withheld contains msg if {
	not input.runner
	msg := "the qml runner is not on this host; the widget did not run"
}
