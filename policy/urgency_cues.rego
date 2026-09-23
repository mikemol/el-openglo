package el.urgency_cues

# W72.h / W74 — is marquee urgency VISIBLE without colour at panel size? The
# measurement is scripts/check_urgency_cues.py --json: per variant, a still and a
# frame series of the real widget per urgency (low / normal / critical), read back
# as a pip grid; a hover-paused critical run; and the charset census of the shipped
# lookup. ⚑ Operator ruling 2026-09-23: urgency is a LETTERFORM — low lowercase,
# normal UPPER CASE, critical FLASHING UPPER CASE — and hue and opacity are colour.

import data.el.fmt
import rego.v1

# first rule: an ABSENT or empty population is a broken search, not a clean board
deny contains "V0: no variant measured: the search is broken" if {
	count(object.get(input, "cases", [])) == 0
	count(object.get(input, "withheld", [])) == 0
}

# SHAPE_MIN — THE PROJECT'S JUDGEMENT, not a standard's. A pair's shape is 1 - IoU of
# the binarised lit pips (brightness normalised away, a +-2 cell slip forgiven), in the
# worst of four views. A 5x7 letter lights ~12-17 pips; 0.15 of the union is ~2 pips
# a letter — more than one pip's sampling slip, the least a reader can see as a
# different letterform. An opacity- or hue-only cue scores 0.
shape_min := 0.15

# the flash: the operator's ceiling (2 Hz) on the DECLARED rate; WCAG 2.2 SC 2.3.1's
# ceiling (no more than 3 flashes in any one second) on the MEASURED one; and the
# measured rate within rate_tolerance of the declared (the frames sample at 40 ms)
operator_max_hz := 2

wcag_max_hz := 3

rate_tolerance := 0.25

# a steady urgency's lit frames never dip below half the series' max
steady_min := 0.5

# the temporal arm must have covered frames to judge from
covered_min := 20

num(x) if is_number(x)

# V1 — two urgencies whose lit-pip SETS barely differ, in the worst view
deny contains msg if {
	some c in object.get(input, "cases", [])
	some p in object.get(c, "pairs", [])
	num(p.shape)
	p.shape < shape_min
	msg := sprintf("V1: %s: %s and %s are indistinguishable by letterform (shape %s < %s under %s; mass ratio %s is colour, not shape)",
		[c.variant, p.a, p.b, fmt.fixed(p.shape, 3), fmt.fixed(shape_min, 2), p.view, fmt.fixed(object.get(p, "mass_ratio", 0), 2)])
}

deny contains msg if {
	some c in object.get(input, "cases", [])
	some p in object.get(c, "pairs", [])
	not num(object.get(p, "shape", null))
	msg := sprintf("V1: %s: %v~%v has no shape measured", [c.variant, object.get(p, "a", "?"), object.get(p, "b", "?")])
}

# V2 — a case missing any of the three urgency pairs has not measured the claim
deny contains msg if {
	some c in object.get(input, "cases", [])
	count(object.get(c, "pairs", [])) != 3
	msg := sprintf("V2: %s: %d of 3 urgency pairs measured", [c.variant, count(object.get(c, "pairs", []))])
}

# V3 — critical keeps its lit underline row: lit in every view
deny contains msg if {
	some c in object.get(input, "cases", [])
	some v, f in object.get(object.get(c, "urgencies", {}), "critical", {})
	ul := object.get(f, "underline", null)
	not ul >= 0.5
	msg := sprintf("V3: %s: critical's underline row is lit in only %v of its span under %s", [c.variant, ul, v])
}

deny contains msg if {
	some c in object.get(input, "cases", [])
	count(object.get(object.get(c, "urgencies", {}), "critical", {})) == 0
	msg := sprintf("V3: %s: no critical still measured", [c.variant])
}

temporal(c, u) := object.get(object.get(c, "temporal", {}), u, {})

# V4 — the temporal arm had frames to judge (text covering the board end to end)
deny contains msg if {
	some c in object.get(input, "cases", [])
	some u in ["low", "normal", "critical"]
	n := object.get(temporal(c, u), "covered", 0)
	not n >= covered_min
	msg := sprintf("V4: %s: %s has %v covered frame(s), fewer than %d: the flash cannot be judged", [c.variant, u, n, covered_min])
}

# V5 — critical FLASHES: it alternates (at least two edges, some dark frames)
deny contains msg if {
	some c in object.get(input, "cases", [])
	t := temporal(c, "critical")
	object.get(t, "covered", 0) >= covered_min
	not object.get(t, "edges", 0) >= 2
	msg := sprintf("V5: %s: critical does not flash (%v edge(s) over %v covered frames): upper case alone is normal's letterform",
		[c.variant, object.get(t, "edges", 0), t.covered])
}

# V6 — ...at a safe rate: the measured rate under WCAG 2.3.1's three per second
deny contains msg if {
	some c in object.get(input, "cases", [])
	hz := object.get(temporal(c, "critical"), "hz", null)
	num(hz)
	hz > wcag_max_hz
	msg := sprintf("V6: %s: critical flashes at %s Hz, over WCAG 2.3.1's %d flashes a second", [c.variant, fmt.fixed(hz, 2), wcag_max_hz])
}

# V7 — ...at the DECLARED rate, and the declared rate within the operator's ceiling
deny contains msg if {
	some c in object.get(input, "cases", [])
	t := temporal(c, "critical")
	object.get(t, "edges", 0) >= 2
	declared := object.get(object.get(input, "charset", {}), "flash_hz", null)
	num(declared)
	num(t.hz)
	abs(t.hz - declared) > rate_tolerance * declared
	msg := sprintf("V7: %s: critical flashes at %s Hz, not the declared %s Hz (+-%d%%)",
		[c.variant, fmt.fixed(t.hz, 2), fmt.fixed(declared, 2), round(rate_tolerance * 100)])
}

deny contains msg if {
	declared := object.get(object.get(input, "charset", {}), "flash_hz", null)
	num(declared)
	declared > operator_max_hz
	msg := sprintf("V7: the declared flash rate %s Hz is over the operator's %d Hz ceiling", [fmt.fixed(declared, 2), operator_max_hz])
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	not num(object.get(object.get(input, "charset", {}), "flash_hz", null))
	msg := "V7: no declared flash rate measured (Body.FLASH_HZ)"
}

# V8 — low and normal are STEADY: no edges, no dip in their lit frames
deny contains msg if {
	some c in object.get(input, "cases", [])
	some u in ["low", "normal"]
	t := temporal(c, u)
	object.get(t, "edges", 0) > 0
	msg := sprintf("V8: %s: %s flashes (%v edges): only critical may", [c.variant, u, t.edges])
}

deny contains msg if {
	some c in object.get(input, "cases", [])
	some u in ["low", "normal"]
	t := temporal(c, u)
	object.get(t, "covered", 0) >= covered_min
	s := object.get(t, "steady_min", null)
	not s >= steady_min
	msg := sprintf("V8: %s: %s's lit mass dips to %v of its max: not steady", [c.variant, u, s])
}

# V9 — the flash is PAUSABLE (WCAG 2.2.2): no dark sample while the hover-pause holds
deny contains msg if {
	some c in object.get(input, "cases", [])
	pz := object.get(c, "pause", {})
	object.get(pz, "paused_dark", 0) > 0
	msg := sprintf("V9: %s: %d of %d samples held by the hover-pause are in the flash's dark phase",
		[c.variant, pz.paused_dark, object.get(pz, "paused_samples", 0)])
}

deny contains msg if {
	some c in object.get(input, "cases", [])
	not object.get(object.get(c, "pause", {}), "paused_samples", 0) > 0
	msg := sprintf("V9: %s: the hover-pause never held the board: pausability not measured", [c.variant])
}

# ...and held it for at least one full flash cycle: a shorter hold could not have
# caught an ungated flash's dark phase
deny contains msg if {
	some c in object.get(input, "cases", [])
	pz := object.get(c, "pause", {})
	object.get(pz, "paused_samples", 0) > 0
	cycle := object.get(object.get(input, "charset", {}), "flash_ms", null)
	num(cycle)
	held := object.get(pz, "paused_ms", null)
	not held >= cycle
	msg := sprintf("V9: %s: the hover-pause held %v ms, under one %s ms flash cycle: pausability not measured",
		[c.variant, held, fmt.fixed(cycle, 0)])
}

# V10 — the charset has the glyph each urgency's letterform needs. A letter whose case
# partner is in the declared charset must land on the displayed form's own glyph; a
# letter that lands on '?' renders a question mark whatever its urgency.
deny contains msg if {
	some row in object.get(object.get(input, "charset", {}), "cases", [])
	some f in object.get(row, "forms", [])
	f.partner_in_charset == true
	f.case_applied != true
	msg := sprintf("V10: %q at urgency %d shows as %q: the registry has no glyph for %q (the case cue is lost)",
		[row.ch, f.urgency, f.key, f.shown])
}

deny contains msg if {
	some row in object.get(object.get(input, "charset", {}), "cases", [])
	some f in object.get(row, "forms", [])
	f.key == "?"
	msg := sprintf("V10: %q at urgency %d renders '?'", [row.ch, f.urgency])
}

deny contains "V10: the charset census measured no letters" if {
	count(object.get(input, "cases", [])) > 0
	count(object.get(object.get(input, "charset", {}), "cases", [])) == 0
}

admitted contains c.variant if {
	some c in object.get(input, "cases", [])
	count(object.get(c, "pairs", [])) == 3
	every p in c.pairs { p.shape >= shape_min }
	object.get(temporal(c, "critical"), "edges", 0) >= 2
}

withheld contains msg if {
	some w in object.get(input, "withheld", [])
	msg := sprintf("%s: %s", [w.variant, w.reason])
}
