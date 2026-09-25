# METADATA
# title: "U0 — no styles measured admits nothing; every declared variant is measured"
# description: |
#   The measurement is `scripts/check_union.py --json`: the declared roster
#   (variant_roster), make_union.VARIANTS' drift from it, the --names Breeze's
#   variables.css defines on this host (null when Union is not installed), and per
#   variant the emitted overrides.css read back — tinycss2's parse-error count
#   (null when tinycss2 is absent), each overridden name with the numbers in its
#   value, and each alpha make_union.alphas() solved. Weakness: the emitted text,
#   not Union's cascade.
package el.union

import data.el.fmt
import rego.v1

deny contains "U0: no styles were measured; the roster is empty, not the styles sound" if {
	count(object.get(input, "cases", [])) == 0
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	some v in input.roster
	not v in {c.id | some c in input.cases}
	msg := sprintf("U0: %s: declared but not measured", [v])
}

deny contains msg if {
	some d in object.get(input, "roster_drift", [])
	msg := sprintf("U0: %s: %s", [d.variant, d.why])
}

# METADATA
# title: "U1 — the emitted CSS parses"
deny contains msg if {
	some c in input.cases
	c.parse_errors != null
	c.parse_errors > 0
	msg := sprintf("U1: %s: %d parse error(s)", [c.id, c.parse_errors])
}

withheld contains msg if {
	some c in input.cases
	c.parse_errors == null
	msg := sprintf("U1: %s: tinycss2 is not installed here; the parse is unmeasured", [c.id])
}

# METADATA
# title: "U2 — every overridden name is one Breeze's variables.css defines"
deny contains msg if {
	object.get(input, "breeze", null) != null
	breeze := {b | some b in input.breeze}
	some c in input.cases
	unknown := {o.name | some o in c.overrides} - breeze
	count(unknown) > 0
	msg := sprintf("U2: %s: overrides Breeze does not define: %v", [c.id, sort(unknown)])
}

withheld contains "U2: Breeze's variables.css is absent here (Union not installed); override-existence is unmeasured" if {
	count(object.get(input, "cases", [])) > 0
	object.get(input, "breeze", null) == null
}

# METADATA
# title: "U3 — every solved alpha is what the override carries"
deny contains msg if {
	some c in input.cases
	some s in c.solved
	s.alpha != null
	not s.var in {o.name | some o in c.overrides}
	msg := sprintf("U3: %s: %s is solved (%s) but not overridden", [c.id, s.var, fmt.fixed(s.alpha, 3)])
}

deny contains msg if {
	some c in input.cases
	some s in c.solved
	s.alpha != null
	some o in c.overrides
	o.name == s.var
	not s.alpha in {n | some n in o.numbers}
	msg := sprintf("U3: %s: %s emits %v, not the solved %s", [c.id, s.var, o.numbers, fmt.fixed(s.alpha, 3)])
}

# METADATA
# title: "U4 — a solved alpha is an alpha: within 0..1"
deny contains msg if {
	some c in input.cases
	some s in c.solved
	s.alpha != null
	not in_unit(s.alpha)
	msg := sprintf("U4: %s: %s solved to %s, outside 0..1", [c.id, s.var, fmt.fixed(s.alpha, 3)])
}

in_unit(a) if {
	a >= 0
	a <= 1
}

carries(c, s) if {
	some o in c.overrides
	o.name == s.var
	s.alpha in {n | some n in o.numbers}
}

admitted contains c.id if {
	some c in input.cases
	c.parse_errors != null
	c.parse_errors == 0
	every s in c.solved {
		solved_ok(c, s)
	}
}

solved_ok(_, s) if s.alpha == null

solved_ok(c, s) if carries(c, s)
