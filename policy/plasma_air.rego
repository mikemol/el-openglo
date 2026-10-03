# METADATA
# title: "P0 — an empty population admits nothing"
# description: |
#   The measurement is `scripts/check_plasma_air.py --json` (W223): per host Plasma
#   Style, whether a colors file ships and, per SVG, how many elements are painted by
#   a ColorScheme-* class vs a literal colour. THE VERDICT is derived here, not in
#   Python: a theme FOLLOWS the scheme only with no colors file and no literal colour
#   in any SVG; otherwise it BAKES, and an EL flavour of it needs a recolour emitter
#   (make_plasma), not a defaults choice (W37). `recorded` is the finding; P1 denies a
#   recorded verdict the host no longer shows, so the finding cannot go stale.
package el.plasma_air

import rego.v1

themes := object.get(input, "themes", [])

# measured verdicts for the themes that could be read
recorded := {"air": "bakes"}

deny contains msg if {
	count(themes) == 0
	msg := "P0: no Plasma Style was measured; the search is broken, not the theme clean"
}

measured contains t if {
	some t in themes
	not object.get(t, "withheld", false)
}

baked_svgs(t) := n if {
	xs := [s.path | some s in t.svgs; s.baked > 0]
	n := count(xs)
}

verdict(t) := "follows" if {
	baked_svgs(t) == 0
	t.has_colors_file == false
}

verdict(t) := "bakes" if {
	not verdict_follows(t)
}

verdict_follows(t) if {
	baked_svgs(t) == 0
	t.has_colors_file == false
}

# P2 — an empty SVG population cannot say "follows"
deny contains msg if {
	some t in measured
	count(t.svgs) == 0
	msg := sprintf("P2: %s has no SVG to measure", [t.id])
}

# P1 — the recorded verdict must match the measured one
deny contains msg if {
	some t in measured
	count(t.svgs) > 0
	want := object.get(recorded, t.id, "unrecorded")
	got := verdict(t)
	want != got
	msg := sprintf("P1: %s is recorded as %s but measures as %s", [t.id, want, got])
}

verdicts[t.id] := verdict(t) if {
	some t in measured
	count(t.svgs) > 0
}

admitted contains t.id if {
	some t in measured
	count(t.svgs) > 0
	object.get(recorded, t.id, "unrecorded") == verdict(t)
}

withheld contains msg if {
	some t in themes
	reason := object.get(t, "withheld", false)
	reason != false
	msg := sprintf("%s: %s", [t.id, reason])
}
