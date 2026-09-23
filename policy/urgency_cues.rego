package el.urgency_cues

# W72.h — is marquee urgency VISIBLE by weight at panel size? The measurement is
# scripts/check_urgency_cues.py --json: per variant, three stills of the real widget
# (urgency low / normal / critical), read back as a pip grid, and per pair of
# urgencies the WORST view's footprint ratio (gray + three CVD simulations; the
# footprint is self-normalised, so brightness — opacity, i.e. colour — cannot carry
# it). The floor is the measurement's `threshold` (WEIGHT_RATIO_MIN, 1.25: typography's
# smallest weight step a reader picks out; the check's docstring says why not 3:1).

import rego.v1

# first rule: an ABSENT or empty population is a broken search, not a clean board
deny contains "V0: no variant measured: the search is broken" if {
	count(object.get(input, "cases", [])) == 0
	count(object.get(input, "withheld", [])) == 0
}

threshold := object.get(input, "threshold", 1.25)

# two urgencies whose lit area differs by less than one weight step, in the worst view
deny contains msg if {
	some c in object.get(input, "cases", [])
	some p in object.get(c, "pairs", [])
	p.ratio < threshold
	msg := sprintf("V1: %s: %s and %s are indistinguishable by weight (footprint ratio %v < %v under %s; brightness ratio %v is colour, not weight)",
		[c.variant, p.a, p.b, p.ratio, threshold, p.view, p.mass_ratio])
}

# a case missing any of the three urgencies has not measured the claim
deny contains msg if {
	some c in object.get(input, "cases", [])
	count(object.get(c, "pairs", [])) != 3
	msg := sprintf("V2: %s: %d of 3 urgency pairs measured", [c.variant, count(object.get(c, "pairs", []))])
}

# critical claims an underline (the descent row lit): it must be lit in every view
deny contains msg if {
	some c in object.get(input, "cases", [])
	some v, f in object.get(object.get(c, "urgencies", {}), "critical", {})
	f.underline < 0.5
	msg := sprintf("V3: %s: critical's underline row is lit in only %v of its span under %s", [c.variant, f.underline, v])
}

admitted contains c.variant if {
	some c in object.get(input, "cases", [])
	count(object.get(c, "pairs", [])) == 3
	every p in c.pairs { p.ratio >= threshold }
}

withheld contains msg if {
	some w in object.get(input, "withheld", [])
	msg := sprintf("%s: %s", [w.variant, w.reason])
}
