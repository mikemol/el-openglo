# METADATA
# title: "fmt — fixed-point formatting a policy message can trust"
# description: |
#   sprintf's %.1f / %.2f / %.4f print an integral JSON number (25.0 arrives as
#   25, an int) as "%!f(int=25)" — the message a gate prints when it DENIES is
#   exactly the one nobody has seen rendered. fixed(x, n) formats through
#   integer arithmetic and %d, so a whole number and a fraction print alike:
#   fixed(25, 2) == "25.00", fixed(3.3333, 2) == "3.33", fixed(-0.05, 1) == "-0.1".
#   Rounding is round-half-away-from-zero (rego's round). n is 0..4.
#
#   ⚑ THIS FILE LIVES IN policy/lib/, NOT policy/: opa_gate.policies() lists
#   policy/*.rego (non-recursive) as check-backed gates, and a library has no
#   check_<name>.py; `opa eval -d policy/` and `opa test policy/` load the tree
#   recursively, so `import data.el.fmt` resolves in every policy and test.
package el.fmt

import rego.v1

scale := {0: 1, 1: 10, 2: 100, 3: 1000, 4: 10000}

fixed(x, 0) := sprintf("%s%d", [sign(x, round(abs(x))), round(abs(x))])

fixed(x, n) := s if {
	n > 0
	k := scale[n]
	m := round(abs(x) * k)
	whole := floor(m / k)
	frac := sprintf("%d", [m - (whole * k)])
	pad := substring("0000", 0, n - count(frac))
	s := sprintf("%s%d.%s%s", [sign(x, m), whole, pad, frac])
}

sign(x, m) := "-" if {
	x < 0
	m != 0
}

sign(x, m) := "" if {
	not x < 0
}

sign(x, m) := "" if {
	m == 0
}
