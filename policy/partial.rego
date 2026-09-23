# METADATA
# title: "P0 — no roster entry measured admits nothing"
# description: |
#   The measurement is `scripts/check_partial.py --json`: each file the recovery
#   recorded as PARTIAL (replayed to an intermediate state; compiles, behaviour
#   unverified), whether it exists, and whether RECOVERY-NOTES.md names it. An
#   empty roster is a broken record, not a clean recovery.
package el.partial

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "P0: no partial-recovery roster entry was measured"
}

# METADATA
# title: "P1 — every file recorded as partial is in the tree"
# description: |
#   A record naming a vanished file is stale, and a stale roster means a reader
#   trusts the wrong set of files as unverified.
deny contains msg if {
	some c in input.cases
	not c.exists
	msg := sprintf("P1: %s is recorded as partial but absent from the tree", [c.file])
}

# METADATA
# title: "P2 — the provenance record is reachable and names every partial file"
# description: |
#   The caveat must meet a reader in the tree: the notes exist, and each partial
#   file is named in them.
deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	not input.notes_present
	msg := sprintf("P2: %s is absent — the provenance record is unreachable", [input.notes])
}

deny contains msg if {
	input.notes_present
	some c in input.cases
	not c.named
	msg := sprintf("P2: %s does not mention %s", [input.notes, c.file])
}

admitted contains c.file if {
	input.notes_present
	some c in input.cases
	c.exists
	c.named
}
