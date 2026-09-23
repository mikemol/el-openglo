# METADATA
# title: "S0 — no record measured admits nothing"
# description: |
#   The measurement is `scripts/check_scope_recorded.py --json`: the record where
#   the rename decision must be legible (RECOVERY-NOTES.md), whether it is present,
#   and the paragraph windows that carry the rationale. A decision item is CLOSED
#   while decided; this keeps it FALSIFIABLE by asking that the decision be legible.
#
#   ⚑ EVERY CASE LANDS IN EXACTLY ONE OF withheld / deny / admitted. `present`
#   (a boolean) and `evidence` (a list) are ALWAYS emitted; null or absent could
#   not be said — S3 withholds it and no rule judges that record.
package el.scope_recorded

import rego.v1

fields := ["present", "evidence"]

measured(c) if {
	every f in fields {
		object.get(c, f, null) != null
	}
}

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "S0: no decision record was measured"
}

# METADATA
# title: "S3 — a fact the measurement did not state is withheld, not judged"
withheld contains msg if {
	some c in object.get(input, "cases", [])
	some f in fields
	object.get(c, f, null) == null
	msg := sprintf("S3: %v: %s was not measured", [object.get(c, "record", null), f])
}

# METADATA
# title: "S1 — the record exists"
deny contains msg if {
	some c in input.cases
	measured(c)
	c.present == false
	msg := sprintf("S1: %s is absent; the rename decision has nowhere legible to live", [c.record])
}

# METADATA
# title: "S2 — the record says WHY the prior mark was retired"
# description: |
#   A reader meeting the rename must find its reason, not only the change.
deny contains msg if {
	some c in input.cases
	measured(c)
	c.present == true
	count(c.evidence) == 0
	msg := sprintf("S2: %s does not record WHY the prior mark was retired", [c.record])
}

admitted contains c.record if {
	some c in input.cases
	measured(c)
	c.present == true
	count(c.evidence) > 0
}
