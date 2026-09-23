# METADATA
# title: "T0 — a document citing no applier admits nothing"
# description: |
#   The measurement is `scripts/check_standards.py --json`: every backticked
#   `module.attr` STANDARDS.md credits with applying a standard, and whether the
#   module imports and carries it. No citation at all means the citation format
#   changed or the scan broke — not that every standard is applied.
package el.standards

import rego.v1

import data.el.truth

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "T0: no cited applier was measured; the document is absent, its citation format changed, or the scan is broken"
}

# METADATA
# title: "T1 — the standards document exists"
deny contains msg if {
	not object.get(input, "doc_present", false)
	msg := "T1: STANDARDS.md is absent; the standards this project applies are recorded nowhere"
}

# METADATA
# title: "T2 — every cited applier resolves"
# description: |
#   The recovery lost most of cvd_gate.py (APCA, WCAG, the q metric) while every
#   file still compiled; a document crediting an absent applier is how that hides.
deny contains msg if {
	some c in input.cases
	c.imports == false
	msg := sprintf("T2: %s.%s: module will not import: %s", [c.module, c.attr, c.error])
}

deny contains msg if {
	some c in input.cases
	truth.py(c.imports)
	c.present == false
	msg := sprintf("T2: %s.%s: named in STANDARDS.md, absent from the module", [c.module, c.attr])
}

# METADATA
# title: "W — an applier whose import or presence was not reported is withheld"
# description: |
#   check_standards always emits `imports` and `present` as bools (present is
#   False on an import failure, where T2 judges `imports` instead). Null or
#   absent means the measurement could not say, so the case is not judged.
withheld contains msg if {
	some c in input.cases
	not is_boolean(object.get(c, "imports", null))
	msg := sprintf("%s.%s: imports was not measured", [c.module, c.attr])
}

withheld contains msg if {
	some c in input.cases
	truth.py(c.imports)
	not is_boolean(object.get(c, "present", null))
	msg := sprintf("%s.%s: present was not measured", [c.module, c.attr])
}

admitted contains sprintf("%s.%s", [c.module, c.attr]) if {
	some c in input.cases
	truth.py(c.imports)
	truth.py(c.present)
}
