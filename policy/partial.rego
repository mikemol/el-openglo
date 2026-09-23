# METADATA
# title: "P0 — no roster entry measured admits nothing"
# description: |
#   The measurement is `scripts/check_partial.py --json`: each file the recovery
#   recorded as PARTIAL (replayed to an intermediate state; compiles, behaviour
#   unverified), whether it exists, and whether RECOVERY-NOTES.md names it. An
#   empty roster is a broken record, not a clean recovery.
#
#   ⚑ EXACTLY ONCE: the measurement always emits `notes_present` and, per case,
#   `exists` and `named` as booleans. One of those null or absent is a
#   could-not-say: the case is WITHHELD by name and no rule judges it
#   (`not c.exists` read null as "exists").
package el.partial

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "P0: no partial-recovery roster entry was measured"
}

# a case whose facts the measurement stated
measured(c) if {
	is_boolean(object.get(c, "exists", null))
	is_boolean(object.get(c, "named", null))
}

withheld contains msg if {
	some c in object.get(input, "cases", [])
	some f in ["exists", "named"]
	not is_boolean(object.get(c, f, null))
	msg := sprintf("P1: %v: %s was not measured", [object.get(c, "file", null), f])
}

withheld contains msg if {
	count(object.get(input, "cases", [])) > 0
	not is_boolean(object.get(input, "notes_present", null))
	msg := "P2: notes_present was not measured"
}

# METADATA
# title: "P1 — every file recorded as partial is in the tree"
# description: |
#   A record naming a vanished file is stale, and a stale roster means a reader
#   trusts the wrong set of files as unverified.
deny contains msg if {
	some c in input.cases
	measured(c)
	c.exists == false
	msg := sprintf("P1: %s is recorded as partial but absent from the tree", [c.file])
}

# METADATA
# title: "P2 — the provenance record is reachable and names every partial file"
# description: |
#   The caveat must meet a reader in the tree: the notes exist, and each partial
#   file is named in them.
deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	input.notes_present == false
	msg := sprintf("P2: %s is absent — the provenance record is unreachable", [input.notes])
}

deny contains msg if {
	input.notes_present == true
	some c in input.cases
	measured(c)
	c.named == false
	msg := sprintf("P2: %s does not mention %s", [input.notes, c.file])
}

admitted contains c.file if {
	input.notes_present == true
	some c in input.cases
	measured(c)
	c.exists == true
	c.named == true
}
