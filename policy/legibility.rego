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
#   The floor is MEASURED (s131, low-pass 1.0 pitch): the 1:1 Unifont x-height band
#   reads 0.786 (caps cut by the band — 'Helio'), 2:1 at γ 0.5 reads 1.000,
#   Liberation Mono reads 1.000. 0.7 sits under the lowest honest read; a snapping
#   field, a wrong γ (γ 1 at 2:1 read NOTHING) or a lost alignment falls below it.
deny contains msg if {
	some c in input.cases
	not c.withheld
	c.lang == "eng"
	c.score < 0.7
	msg := sprintf("G2: %s reads %q for %q — score %.3f, below the 0.7 floor", [c.label, c.read, c.text, c.score])
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
