# METADATA
# title: "T0 — pairs are declared"
# description: |
#   The measurement is `scripts/check_template_parity.py --json`: per declared
#   (generator accessor, baseline) pair, whether the baseline exists and its inode's
#   link count, and when the pair could be evaluated whether the generator's output
#   equals the baseline byte for byte (with both sizes); `skip` names a pinned host
#   file that is absent, `raised` the generator's exception. Extraction must be
#   output-neutral, and a recorded baseline is how that is shown, not said.
package el.template_parity

import rego.v1

deny contains "T0: no pairs were declared; the check is vacuous, not the templates faithful" if {
	count(object.get(input, "cases", [])) == 0
}

# METADATA
# title: "T1 — a missing baseline is a refusal, not a pass"
deny contains msg if {
	some c in input.cases
	c.baseline_present == false
	msg := sprintf("T1: %s: NO BASELINE (%s) — parity is unverified, not confirmed", [c.id, c.baseline])
}

# METADATA
# title: "T2 — a baseline is an independent record (its own inode)"
# description: |
#   Measured 2026-09-21: a dedup pass hard-linked a baseline to the template it
#   certifies, so editing the template edited its baseline and parity could not
#   fail. `check_template_parity.py --unlink` gives each its own inode.
deny contains msg if {
	some c in input.cases
	is_number(c.links)
	c.links > 1
	msg := sprintf("T2: %s: SHARED INODE (%s: %d links) — not an independent record; run --unlink", [c.id, c.baseline, c.links])
}

# METADATA
# title: "T3 — the generator runs and emits its baseline byte for byte"
deny contains msg if {
	some c in input.cases
	is_string(c.raised)
	msg := sprintf("T3: %s: RAISED %s", [c.id, c.raised])
}

deny contains msg if {
	some c in input.cases
	c.equal == false
	msg := sprintf("T3: %s: DIFFERS (%d vs %d bytes) — read --diff, then --record only if the change is intended", [c.id, c.got_bytes, c.want_bytes])
}

# a pinned host file (the marquee's font) is absent: a fact about the host
withheld contains msg if {
	some c in input.cases
	is_string(c.skip)
	msg := sprintf("T3: %s: SKIP (%s)", [c.id, c.skip])
}

withheld contains msg if {
	some c in input.cases
	c.baseline_present == true
	c.skip == null
	c.raised == null
	not is_boolean(c.equal)
	msg := sprintf("W: %s: equal was not measured", [c.id])
}

admitted contains c.id if {
	some c in input.cases
	c.baseline_present == true
	c.links == 1
	c.equal == true
}
