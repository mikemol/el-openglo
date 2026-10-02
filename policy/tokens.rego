# METADATA
# title: "D0 — no variant measured admits nothing"
# description: |
#   The measurement is `scripts/check_tokens.py --json`: per variant the palette
#   declares (variant_roster), whether catalog/el-openglo.tokens.json has its DTCG
#   group, its colour and alpha leaf counts, every leaf not in this file's DTCG shape,
#   and whether the committed file equals a fresh make_tokens.document(). W160.
package el.tokens

import rego.v1

deny contains "D0: no variant was measured; the roster is empty, not the token file complete" if {
	count(object.get(input, "cases", [])) == 0
	count(object.get(input, "withheld", [])) == 0
}

# METADATA
# title: "D1 — every declared variant has its group"
deny contains msg if {
	some c in input.cases
	c.present == false
	msg := sprintf("D1: %s: the token file has no group for this variant", [c.variant])
}

# METADATA
# title: "D2 — every leaf is valid DTCG in this file's shape (color #rrggbb, number numeric)"
deny contains msg if {
	some c in input.cases
	c.present == true
	some p in c.bad
	msg := sprintf("D2: %s: leaf %s is not a valid DTCG color/number", [c.variant, p])
}

# METADATA
# title: "D3 — a variant carries colours and both solved alphas"
deny contains msg if {
	some c in input.cases
	c.present == true
	c.colors == 0
	msg := sprintf("D3: %s: no colour tokens", [c.variant])
}

deny contains msg if {
	some c in input.cases
	c.present == true
	c.alphas < 2
	msg := sprintf("D3: %s: %d of 2 solved alphas", [c.variant, c.alphas])
}

# METADATA
# title: "D4 — the committed file is current (equals a fresh emission from the palette)"
deny contains "D4: catalog/el-openglo.tokens.json is stale; run make_tokens.py" if {
	input.current == false
}

# METADATA
# title: "D5 — a variant carries the engine material (W151): base, emissive, ghost, ghost_opacity"
material_slots := {"base", "emissive", "ghost", "ghost_opacity", "hue", "floors"}

deny contains msg if {
	some c in input.cases
	c.present == true
	some s in material_slots
	not s in {m | some m in object.get(c, "materials", [])}
	msg := sprintf("D5: %s: material slot %s is missing", [c.variant, s])
}

withheld contains msg if {
	some msg in object.get(input, "withheld", [])
}

admitted contains c.variant if {
	some c in input.cases
	c.present == true
	count(c.bad) == 0
	c.colors > 0
	c.alphas == 2
	material_slots == {m | some m in object.get(c, "materials", [])}
}
