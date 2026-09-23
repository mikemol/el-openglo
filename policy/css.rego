# METADATA
# title: "K0 — no variants measured admits nothing"
# description: |
#   The measurement is `scripts/check_css.py --json`: whether
#   catalog/el-openglo.css exists; per variant, the custom properties the token
#   dict implies (`expected`, as make_css would emit them) and the ones the
#   stylesheet's [data-el-variant] block carries once parsed by tinycss2 (`got`,
#   null when the block is absent); and the parsed :root and
#   prefers-color-scheme: light blocks. tinycss2 absent is WITHHELD — the sheet
#   is unparsed, not wrong. A STALE FILE IS THE DEFECT: values are compared, not
#   presence. Weakness: tinycss2 tokenizes, it does not evaluate color-mix().
package el.css

import rego.v1

import data.el.truth

# stated beside the tokens: derived identities and flags, not tokens themselves
derived := {"--el-fg-in-seen", "--el-fg-in-seen-glanced", "--el-ghost-alpha-glanced-infeasible", "--el-tt-is-sel"}

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "K0: no variants were measured; the token grid is empty, not the sheet correct"
}

deny contains msg if {
	input.file_present == false
	msg := "K0: catalog/el-openglo.css absent; run make_css.py"
}

withheld contains msg if {
	input.parsed == false
	msg := "K0: tinycss2 not importable — the stylesheet is unparsed, not wrong"
}

# METADATA
# title: "K1 — every variant block carries every token at the token's value"
deny contains msg if {
	truth.py(input.parsed)
	some c in input.cases
	c.got == null
	msg := sprintf("K1: %s: no [data-el-variant=%q] block", [c.id, c.id])
}

deny contains msg if {
	truth.py(input.parsed)
	some c in input.cases
	c.got != null
	some prop, want in c.expected
	not prop in object.keys(c.got)
	msg := sprintf("K1: %s: %s missing", [c.id, prop])
}

deny contains msg if {
	truth.py(input.parsed)
	some c in input.cases
	c.got != null
	some prop, want in c.expected
	have := c.got[prop]
	have != want
	msg := sprintf("K1: %s: %s = %q, token says %q", [c.id, prop, have, want])
}

# METADATA
# title: "K2 — no --el- property that is not a token"
deny contains msg if {
	truth.py(input.parsed)
	some c in input.cases
	c.got != null
	some prop, _ in c.got
	startswith(prop, "--el-")
	not prop in object.keys(c.expected)
	not prop in derived
	msg := sprintf("K2: %s: %s is not a token", [c.id, prop])
}

# METADATA
# title: "K3 — the seen ghost is stated as color-mix(fg_in over view)"
deny contains msg if {
	truth.py(input.parsed)
	some c in input.cases
	c.got != null
	some prop in ["--el-fg-in-seen", "--el-fg-in-seen-glanced"]
	not is_mix(object.get(c.got, prop, ""))
	msg := sprintf("K3: %s: %s is not color-mix(fg_in over view)", [c.id, prop])
}

is_mix(v) if {
	startswith(v, "color-mix(")
	contains(v, "--el-fg-in")
	contains(v, "--el-view")
}

# METADATA
# title: "K4 — the Off/Lit polarity maps onto prefers-color-scheme"
deny contains msg if {
	truth.py(input.parsed)
	not polarity(input.root, "EL-Openglo")
	msg := "K4: :root is not EL-Openglo"
}

deny contains msg if {
	truth.py(input.parsed)
	not polarity(input.light, "EL-Openglo-Lit")
	msg := "K4: prefers-color-scheme: light is not EL-Openglo-Lit"
}

polarity(block, vid) if {
	block != null
	some c in input.cases
	c.id == vid
	block == c.got
}

admitted contains c.id if {
	truth.py(input.parsed)
	some c in input.cases
	c.got != null
	every prop, want in c.expected { c.got[prop] == want }
}
