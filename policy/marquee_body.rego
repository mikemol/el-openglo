# METADATA
# title: M0 — an empty population admits nothing
# description: |
#   The measurement is `scripts/check_marquee_body.py --json`: the shipped
#   marquee-body.js run headless under Qt's qml on every case, each with the
#   EXPECTED result beside what the parser RETURNED. No cases measured means
#   the harness did not run, not that the parser is right.
package el.marquee_body

import rego.v1

import data.el.truth

deny contains msg if {
	truth.py(input.runner)
	count(input.parse) + count(input.join) + count(input.ring) == 0
	msg := "M0: no cases were measured; the population is empty, not the parser right"
}

# METADATA
# title: M1 — a body parses to the stated text, with the stated style runs, and no tag survives
# description: |
#   The freedesktop spec's legal set (<b> <i> <u> <a href> <img alt>) plus
#   Plasma's <br> and entities; an unknown tag is dropped, an unclosed one kept.
#   A tag surviving INTO the text is what scrolled across the board live (W39).
deny contains msg if {
	some c in input.parse
	c.text != c.expected_text
	msg := sprintf("M1: %q parsed to %q, expected %q", [c.body, c.text, c.expected_text])
}

deny contains msg if {
	some c in input.parse
	c.runs != c.expected_runs
	msg := sprintf("M1: %q styled runs %v, expected %v", [c.body, c.runs, c.expected_runs])
}

deny contains msg if {
	some c in input.parse
	contains(c.text, "<")
	not contains(c.expected_text, "<")
	msg := sprintf("M1: %q: a tag survived into the text %q", [c.body, c.text])
}

# METADATA
# title: M2 — the summary is plain; only the body is markup
# description: |
#   Operator, live (W45): `notify-send 'oh <b>hi</b>'` put markup in the SUMMARY,
#   which the spec reserves for the body; the stock popup showed it literally.
#   joinItem pushes app and summary as text and parses only the body.
deny contains msg if {
	some c in input.join
	c.text != c.expected_text
	msg := sprintf("M2: join%v gave %q, expected %q", [c.args, c.text, c.expected_text])
}

deny contains msg if {
	some c in input.join
	c.runs != c.expected_runs
	msg := sprintf("M2: join%v styled runs %v, expected %v", [c.args, c.runs, c.expected_runs])
}

# METADATA
# title: M3 — the traversal invariant, stepped
# description: |
#   Operator (W45): a notification is never removed while visible; it always
#   scrolls offscreen→onscreen→offscreen at least once; never "just appears",
#   never vanishes, never tears. Each scenario's trace (ring ids and queue ids
#   at every boundary) must equal what the scenario states.
deny contains msg if {
	some s in input.ring
	some i, step in s.trace
	want := s.expected[i]
	step.ring != want.ring
	msg := sprintf("M3: %s: boundary %d rang %v, expected %v", [s.label, i, step.ring, want.ring])
}

deny contains msg if {
	some s in input.ring
	some i, step in s.trace
	want := s.expected[i]
	step.queue != want.queue
	msg := sprintf("M3: %s: boundary %d left queue %v, expected %v", [s.label, i, step.queue, want.queue])
}

deny contains msg if {
	some s in input.ring
	count(s.trace) != count(s.expected)
	msg := sprintf("M3: %s: %d boundaries traced, %d stated", [s.label, count(s.trace), count(s.expected)])
}

# METADATA
# title: "M4 — every arrival is shown: an id that arrives at step s appears in some ring at a step >= s"
# description: |
#   Derived from the steps, not from the stated expectation — a scenario whose
#   expectation itself forgot an arrival would pass M3 and fail here.
arrivals contains {"label": s.label, "id": id, "step": i} if {
	some s in input.ring
	some i, step in s.steps
	some id in step.arrive
}

shown_after(s, id, i) if {
	some j, step in s.trace
	j >= i
	id in step.ring
}

deny contains msg if {
	some a in arrivals
	some s in input.ring
	s.label == a.label
	not shown_after(s, a.id, a.step)
	msg := sprintf("M4: %s: %q arrived at boundary %d and was never rung", [a.label, a.id, a.step])
}

# METADATA
# title: "M6 — a boundary that states its joined text produces it"
# description: |
#   W46: an item's actions join as " [Label]" runs after its text — the
#   scenario states the text it expects at that boundary.
deny contains msg if {
	some s in input.ring
	some i, step in s.steps
	# STATED means present and non-null: an expected "" is still a statement
	step.text != null
	s.trace[i].text != step.text
	msg := sprintf("M6: %s: boundary %d joined %q, expected %q", [s.label, i, s.trace[i].text, step.text])
}

# METADATA
# title: "M7 — a boundary that states a job's series produces it"
# description: |
#   W46 jobs: a progress replace grows the item's history without re-owing a
#   rotation, and the join carries the history as a series run; the scenario
#   states the series per item at that boundary.
deny contains msg if {
	some s in input.ring
	some i, step in s.steps
	# STATED means present and non-null: an expected [] is still a statement
	step.series != null
	s.trace[i].series != step.series
	msg := sprintf("M7: %s: boundary %d series %v, expected %v", [s.label, i, s.trace[i].series, step.series])
}

# METADATA
# title: "M5 — a series becomes the stated column heights"
# description: |
#   W48 (folded into W54): seriesToColumns is pure — a ramp fills the rows, a
#   flat series is a baseline of one (a signal with no range reads as a line,
#   not as nothing), an out-of-range value clamps, an empty series is no
#   columns, a non-number is a zero column. Every case's columns must equal
#   what the case states; a pure function that drifts fails here.
deny contains msg if {
	some c in input.series
	c.columns != c.expected
	msg := sprintf("M5: %s: columns %v, expected %v", [c.label, c.columns, c.expected])
}

deny contains msg if {
	truth.py(input.runner)
	count(input.series) == 0
	msg := "M5: no series cases were measured"
}

# METADATA
# title: "W — the qml runner is absent: nothing measured, nothing admitted"
withheld contains msg if {
	not input.runner
	msg := "the qml runner is not on this host; 0 cases ran"
}
