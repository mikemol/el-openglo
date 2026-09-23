# METADATA
# title: S0 — a log with no el.ident boot admits nothing
# description: |
#   The measurement is `scripts/read_serial.py --json LOG` (el-serial/1,
#   catalog/guest-image.md (f)). A case is one boot that sent an el.ident. A log
#   of console noise only, or one whose el.ident was lost, has no case: the
#   population is empty, not the probe clean. `object.get` so that an ABSENT
#   population is empty too (count(input.cases) is undefined on {}).
#
#   ⚑ EVERY BOOT LANDS IN EXACTLY ONE OF withheld / deny / admitted. A case
#   always carries `probe` (from its el.ident) and `kinds` (kind -> count, each
#   >= 1); null or absent there is "could not say", withheld by W and judged by
#   no rule. `done` is legitimately null (S1 denies it). A null / absent
#   `withheld` list is "nothing withheld", not a withholding.
package el.serial

import rego.v1

import data.el.truth

fields := ["probe", "kinds"]

measured(c) if {
	every f in fields {
		object.get(c, f, null) != null
	}
}

held(c) if truth.py(object.get(c, "withheld", null))

# the boots a rule may judge: fully measured, nothing withheld on them. A boot
# with a gap or a bad frame is WITHHELD only — its facts are not partial data
# to be denied on (a missing el.done beside a gap is the gap's consequence).
judged contains c if {
	some c in object.get(input, "cases", [])
	measured(c)
	not held(c)
}

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "S0: no boot with an el.ident was read; the population is empty, not the probe clean"
}

# The REQUIREMENT: what each probe (el.ident's `probe`, from the cmdline
# `el.probe=`) must have emitted. Kept here, not in guest/el-serial-spec.json,
# because it is a requirement and the spec is the wire format.
required := {
	"P1": {"el.ident", "el.greeter", "el.journal", "el.done"},
	"P2": {"el.ident", "el.session", "el.settled", "el.journal", "el.file", "el.done"},
	"P3": {"el.ident", "el.journal", "el.done"},
	"P4": {"el.ident", "el.session", "el.analyze", "el.done"},
	"P4g": {"el.ident", "el.greeter", "el.analyze", "el.done"},
}

# METADATA
# title: S1 — every boot ends in el.done
# description: |
#   el.done is what covers the tail: a frame lost after the last one received
#   is invisible to the reader's gap detection unless el.done is missing.
case_deny contains {"boot": c.boot, "msg": sprintf("S1: boot %s (probe %v) has no el.done; its tail is unaccounted for", [c.boot, c.probe])} if {
	some c in judged
	object.get(c, "done", null) == null
}

# METADATA
# title: S2 — the probe is one this policy knows
case_deny contains {"boot": c.boot, "msg": sprintf("S2: boot %s names probe %v, which has no requirement here", [c.boot, c.probe])} if {
	some c in judged
	not c.probe in object.keys(required)
}

# METADATA
# title: S3 — every kind the probe requires was received
case_deny contains {"boot": c.boot, "msg": sprintf("S3: boot %s (probe %s) sent no %s", [c.boot, c.probe, k])} if {
	some c in judged
	some k in required[c.probe]
	# kinds maps kind -> count (>= 1); an absent key is a kind not received
	object.get(c.kinds, k, 0) == 0
}

# METADATA
# title: S4 — el.done names the probe el.ident named
case_deny contains {"boot": c.boot, "msg": sprintf("S4: boot %s: el.ident says %v, el.done says %v", [c.boot, c.probe, c.done.probe])} if {
	some c in judged
	c.done.probe != c.probe
}

deny contains x.msg if some x in case_deny

# METADATA
# title: W — a gap, a mismatch or a malformed frame is WITHHELD, never partial data
# description: |
#   The reader reports each as a string on the case (or at log level for a frame
#   it could not assign to a boot). Could-not-measure is kept apart from defect.
withheld contains msg if {
	some c in object.get(input, "cases", [])
	held(c)
	some r in c.withheld
	msg := sprintf("boot %s: %s", [c.boot, r])
}

withheld contains msg if {
	some c in object.get(input, "cases", [])
	some f in fields
	object.get(c, f, null) == null
	msg := sprintf("boot %v: %s was not measured", [object.get(c, "boot", null), f])
}

withheld contains msg if {
	some r in object.get(input, "withheld", [])
	msg := sprintf("log: %s", [r])
}

# A boot is judged and admitted when nothing denied it and nothing was withheld on it.
admitted contains c.boot if {
	some c in judged
	not denied_boot(c.boot)
}

denied_boot(b) if {
	some x in case_deny
	x.boot == b
}
