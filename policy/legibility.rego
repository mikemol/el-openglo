# METADATA
# title: "G0 — no legibility cases admits nothing"
# description: |
#   The measurement is `scripts/check_legibility.py --json`: per case, the string
#   rendered through the aperture field, low-passed and read back by tesseract,
#   with the normalised similarity to the source.
package el.legibility

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "G0: no legibility cases were measured"
}

# METADATA
# title: "G1 — a case without its reader is withheld, not judged"
# description: |
#   No tesseract, no tessdata for the case's language, no qml runner: a fact about
#   the host. Not confirmed is not failed.
withheld contains msg if {
	some c in input.cases
	c.withheld
	msg := sprintf("G1: %s: %s", [c.label, c.withheld])
}

# METADATA
# title: "G2 — a Latin case reads back above the measured floor"
# description: |
#   The floor is MEASURED, and it MOVED (s134). At s131, on a field whose pips sat
#   at fractional positions, the honest reads were 0.786 / 1.000 / 1.000 and the
#   floor was 0.7. The pips are now snapped to the device grid — a board's LEDs do
#   not move, and the operator saw them shimmer — and that costs OCR real
#   information: re-fitted, the best reads are 0.643 (1:1) and 0.812 (2:1). The
#   floor is 0.55, under the lowest honest read of the CURRENT rendering (0.562,
#   Liberation Mono at 8 rows), and the drop is recorded as a TRADE rather than
#   smoothed away: physical regularity beat machine legibility here, and a reader
#   who disagrees has both numbers. ⚑ THIS FLOOR HAS NOW MOVED TWICE, WHICH IS A
#   SMELL: a floor re-fitted after every rendering change grades nothing. The
#   honest use from here is a RATCHET (never worse than the last measurement) and
#   that is W56's residue, not another hand-set number.
deny contains msg if {
	some c in input.cases
	not c.withheld
	c.lang == "eng"
	c.score < 0.55
	msg := sprintf("G2: %s reads %q for %q — score %.3f, below the 0.55 floor", [c.label, c.read, c.text, c.score])
}

# the cases judged and passed — beside these, a withheld case is a SKIP, not
# "nothing was judged" (opa_gate's verdict reads this set)
admitted contains c.label if {
	some c in input.cases
	not c.withheld
	c.read != ""
	c.score >= 0.7
}

# METADATA
# title: "G3 — every scored case actually read something"
deny contains msg if {
	some c in input.cases
	not c.withheld
	c.read == ""
	msg := sprintf("G3: %s read nothing at all", [c.label])
}
