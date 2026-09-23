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

import data.el.truth

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "A0: no consumer references to segment_topology were found; the search is broken, not the API complete"
}

# METADATA
# title: "A1 — the module is in the tree"
deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	input.module_present == false
	msg := "A1: segment_topology.py is absent"
}

# METADATA
# title: "W — a module_present the measurement did not report judges nothing"
# description: |
#   check_st_api always emits module_present as a bool; null or absent means
#   the module was not read, so no case can be judged against it.
withheld contains msg if {
	count(object.get(input, "cases", [])) > 0
	not is_boolean(object.get(input, "module_present", null))
	msg := "module_present was not measured; no referenced symbol was judged"
}

# a symbol whose exported fact is null / absent was not measured
withheld contains msg if {
	truth.py(input.module_present)
	some c in input.cases
	not is_boolean(object.get(c, "exported", null))
	msg := sprintf("%s: exported was not measured", [c.symbol])
}

# METADATA
# title: "A2 — every symbol a consumer references is exported"
# description: |
#   The recovery's notes called the segment API "the main rebuild gap" long
#   after most of it was back; measured, only the 22-segment geometry was
#   missing. This computes that gap instead of recording it.
deny contains msg if {
	truth.py(input.module_present)
	some c in input.cases
	c.exported == false
	msg := sprintf("A2: ST.%s is not exported (referenced by %s)", [c.symbol, concat(", ", c.files)])
}

admitted contains c.symbol if {
	truth.py(input.module_present)
	some c in input.cases
	truth.py(c.exported)
}
