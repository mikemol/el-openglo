# METADATA
# title: "G0 — no legibility cases admits nothing"
# description: |
#   The measurement is `scripts/check_legibility.py --json`: per case, the string
#   rendered through the aperture field, low-passed and read back by tesseract,
#   with the normalised similarity to the source.
#
#   ⚑ EVERY CASE LANDS IN EXACTLY ONE OF withheld / deny / admitted:
#     withheld  G1  the host could not read it (no tesseract, tessdata, runner)
#               G4  it was read, but no floor is declared for it (a non-Latin
#                   language, or a read with no numeric score)
#     deny      G3  it read nothing; G2  a Latin read below `floor`
#     admitted      a Latin read at or above `floor`
#   Until 2026-09-23 `admitted` still used the s131 floor (0.7) while G2 had
#   moved to 0.55 at s134, so every read in [0.55, 0.7) — the CURRENT honest
#   reads, 0.562 and 0.643 — was neither denied nor admitted: silently unjudged.
#   One `floor`, read by both rules, makes that band unrepresentable.
package el.legibility

import rego.v1

import data.el.fmt
import data.el.truth

# G2's floor — see G2 for why it is 0.55 and why it moved. Both the deny and the
# admit read THIS constant; a second literal is how the gap above opened.
floor := 0.55

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "G0: no legibility cases were measured"
}

# measured: the host read it. A null / "" withheld is NOT a withholding reason
# (`not c.withheld` would treat null as one and drop the case from every rule).
measured(c) if not truth.py(object.get(c, "withheld", null))

read_of(c) := object.get(c, "read", "")

# a case the floor applies to: a Latin read with a numeric score
floored(c) if {
	c.lang == "eng"
	is_number(c.score)
}

# METADATA
# title: "G1 — a case without its reader is withheld, not judged"
# description: |
#   No tesseract, no tessdata for the case's language, no qml runner: a fact about
#   the host. Not confirmed is not failed.
withheld contains msg if {
	some c in input.cases
	truth.py(c.withheld)
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
	measured(c)
	floored(c)
	c.score < floor
	msg := sprintf("G2: %s reads %q for %q — score %s, below the %s floor", [c.label, read_of(c), c.text, fmt.fixed(c.score, 3), fmt.fixed(floor, 2)])
}

# the cases judged and passed — beside these, a withheld case is a SKIP, not
# "nothing was judged" (opa_gate's verdict reads this set)
admitted contains c.label if {
	some c in input.cases
	measured(c)
	read_of(c) != ""
	floored(c)
	c.score >= floor
}

# METADATA
# title: "G3 — every scored case actually read something"
deny contains msg if {
	some c in input.cases
	measured(c)
	read_of(c) == ""
	msg := sprintf("G3: %s read nothing at all", [c.label])
}

# METADATA
# title: "G4 — a read with no declared floor is withheld, not admitted"
# description: |
#   The floor is fitted to Latin reads of `Hello world 42`. A non-Latin case
#   (cjk-unifont-1to1, when chi_sim tessdata is installed) or a read that carries
#   no numeric score has no floor to be judged against: it is reported with its
#   score, and it neither passes nor fails. Declaring a floor for it is the fix.
withheld contains msg if {
	some c in input.cases
	measured(c)
	read_of(c) != ""
	not floored(c)
	msg := sprintf("G4: %s (%v) read %q, score %v — no floor is declared for it, so it is not judged", [c.label, object.get(c, "lang", null), read_of(c), object.get(c, "score", null)])
}
