# METADATA
# title: "R0 — a lint that parsed no policy measured nothing"
# description: |
#   The measurement is `scripts/check_rego_lint.py --json`: every tracked
#   policy/**.rego parsed by `opa parse`, its bare-reference conditions
#   (`truthy`) and its float-verb sprintf formats (`fixed`). An empty file
#   population is a broken search, not a clean tree.
package el.rego_lint

import rego.v1

deny contains msg if {
	count(object.get(input, "files", [])) == 0
	msg := "R0: no policy file was in the lint's scope"
}

# METADATA
# title: "T1 — no bare VALUE reference as a condition"
# description: |
#   REGO NULL IS TRUTHY: `c.withheld` alone succeeds on null, "", 0 and [].
#   An unrecognised or null field then fires a rule meant for a real value.
#   Say what is meant: `truth.py(x)` (the measurement's Python truthiness,
#   policy/lib/truth.rego), `x == true`, `x != null`, `count(x) > 0`.
#   A reference to a RULE (`helper`, `pkg.deny`) is recorded, not judged: the
#   rule's own body decides when it is defined.
deny contains msg if {
	some t in object.get(input, "truthy", [])
	t.value == true
	msg := sprintf("T1: %s:%d `%s` is a bare %s reference — null, \"\", 0 and [] fire it; use truth.py(...) or compare", [t.module, t.line, t.text, t.root])
}

# METADATA
# title: "N1 — no `not <value ref>`: `not null` is false"
# description: |
#   `not c.withheld` with withheld == null does not fire, so null reads as a
#   withholding and the case leaves every rule — unjudged. Say what null means:
#   `not truth.py(object.get(c, "withheld", null))` when null is falsy,
#   `c.present == false` (with a withheld message for null) when null is
#   "not measured".
deny contains msg if {
	some t in object.get(input, "negated", [])
	t.value == true
	msg := sprintf("N1: %s:%d `not %s` treats null as present; say what null means", [t.module, t.line, t.text])
}

# METADATA
# title: "F1 — no float verb in a sprintf format"
# description: |
#   sprintf's %.Nf prints an integral JSON number (25.0 arrives as the int 25)
#   as "%!f(int=25)", in the deny message nobody has seen rendered. Format with
#   fmt.fixed(x, n) (policy/lib/fmt.rego) and %s.
deny contains msg if {
	some f in object.get(input, "fixed", [])
	msg := sprintf("F1: %s:%d sprintf format %q holds %v; format the number with fmt.fixed", [f.module, f.line, f.format, f.verbs])
}

withheld contains msg if {
	some u in object.get(input, "unreadable", [])
	msg := sprintf("R0: %s withheld: %s", [u.module, u.withheld])
}

admitted contains f if {
	some f in object.get(input, "files", [])
	not f in {u.module | some u in object.get(input, "unreadable", [])}
}
