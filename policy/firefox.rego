# METADATA
# title: "X0 — no manifests measured admits nothing; every declared variant is measured"
# description: |
#   The measurement is `scripts/check_firefox.py --json`: the declared roster
#   (make_schemes.GRID), make_firefox.VARIANTS' drift from it, and per variant
#   what its emitted manifest.json SAYS — the JSON error (null when it parses),
#   the required colour keys absent, each colour that is not its palette role,
#   each colour key no role maps, the color_scheme found and the one the
#   polarity wants, the gecko id, and web-ext lint's errors (null when web-ext
#   is not installed). Weakness: the manifest, not Firefox's render.
package el.firefox

import rego.v1

deny contains "X0: no manifests were measured; the roster is empty, not the themes sound" if {
	count(object.get(input, "cases", [])) == 0
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	some v in object.get(input, "roster", [])
	not v in {c.id | some c in input.cases}
	msg := sprintf("X0: %s: declared but not measured", [v])
}

deny contains msg if {
	some d in object.get(input, "roster_drift", [])
	msg := sprintf("X0: %s: %s", [d.variant, d.why])
}

# METADATA
# title: "X1 — the manifest parses as JSON"
deny contains msg if {
	some c in input.cases
	is_string(c.parse_error)
	msg := sprintf("X1: %s: manifest.json does not parse: %s", [c.id, c.parse_error])
}

# METADATA
# title: "X2 — frame and tab_background_text are present (Firefox refuses a theme without them)"
deny contains msg if {
	some c in input.cases
	is_array(c.missing_required)
	count(c.missing_required) > 0
	msg := sprintf("X2: %s: required colour key(s) absent: %v", [c.id, c.missing_required])
}

# METADATA
# title: "X3 — every colour is its palette role, and every colour key is mapped"
deny contains msg if {
	some c in input.cases
	is_array(c.wrong_colours)
	some w in c.wrong_colours
	msg := sprintf("X3: %s: %s = %v, not its role %s = %v", [c.id, w.key, w.got, w.role, w.want])
}

deny contains msg if {
	some c in input.cases
	is_array(c.unmapped_keys)
	count(c.unmapped_keys) > 0
	msg := sprintf("X3: %s: colour key(s) no palette role maps: %v", [c.id, c.unmapped_keys])
}

# METADATA
# title: "X4 — color_scheme is dark for an Off variant and light for a Lit one"
deny contains msg if {
	some c in input.cases
	c.parse_error == null
	c.color_scheme != c.want_scheme
	msg := sprintf("X4: %s: color_scheme is %v, the variant's polarity wants %v", [c.id, c.color_scheme, c.want_scheme])
}

# METADATA
# title: "X5 — a stable gecko id naming the variant (AMO signs one theme per id)"
deny contains msg if {
	some c in input.cases
	is_string(c.gecko_id)
	not contains(c.gecko_id, lower(c.id))
	msg := sprintf("X5: %s: gecko id %q does not name the variant", [c.id, c.gecko_id])
}

# METADATA
# title: "X6 — web-ext lint reports no error"
deny contains msg if {
	some c in input.cases
	is_array(c.lint_errors)
	some e in c.lint_errors
	msg := sprintf("X6: %s: web-ext: %s", [c.id, e])
}

withheld contains msg if {
	some c in input.cases
	c.parse_error == null
	not is_array(c.lint_errors)
	msg := sprintf("X6: %s: web-ext is not installed here; the lint is unmeasured", [c.id])
}

# exactly-once: a manifest that parsed but left a fact null was not fully read
unmeasured(c) := {k |
	c.parse_error == null
	some k in ["missing_required", "wrong_colours", "unmapped_keys"]
	not is_array(object.get(c, k, null))
} | {k |
	c.parse_error == null
	some k in ["color_scheme", "gecko_id", "want_scheme"]
	not is_string(object.get(c, k, null))
}

withheld contains msg if {
	some c in input.cases
	some k in unmeasured(c)
	msg := sprintf("W: %s: %s was not measured", [c.id, k])
}

denied_ids contains c.id if {
	some c in input.cases
	some m in deny
	contains(m, sprintf(": %s:", [c.id]))
}

admitted contains c.id if {
	some c in input.cases
	c.parse_error == null
	count(unmeasured(c)) == 0
	not c.id in denied_ids
}
