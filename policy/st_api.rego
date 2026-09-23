# METADATA
# title: "A0 — no referenced symbol measured admits nothing"
# description: |
#   The measurement is `scripts/check_st_api.py --json`: every `ST.<name>` a
#   git-tracked consumer references (in a file importing segment_topology as
#   ST), the files naming it, and whether segment_topology.py exports it. The
#   required set is DISCOVERED from the consumers, never hand-listed; if the
#   discovery finds nothing, the search is broken, not the API complete.
package el.st_api

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "A0: no consumer references to segment_topology were found; the search is broken, not the API complete"
}

# METADATA
# title: "A1 — the module is in the tree"
deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	not input.module_present
	msg := "A1: segment_topology.py is absent"
}

# METADATA
# title: "A2 — every symbol a consumer references is exported"
# description: |
#   The recovery's notes called the segment API "the main rebuild gap" long
#   after most of it was back; measured, only the 22-segment geometry was
#   missing. This computes that gap instead of recording it.
deny contains msg if {
	input.module_present
	some c in input.cases
	not c.exported
	msg := sprintf("A2: ST.%s is not exported (referenced by %s)", [c.symbol, concat(", ", c.files)])
}

admitted contains c.symbol if {
	input.module_present
	some c in input.cases
	c.exported
}
