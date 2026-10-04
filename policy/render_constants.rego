# METADATA
# title: "C0 — no templates measured admits nothing"
# description: |
#   The measurement is `scripts/check_render_constants.py --json`: every property a QML
#   template declares with a LITERAL default, whether a kcfg key reaches it, and the
#   disposition catalog/render-constants.json records for one no key reaches. Operator
#   rule (W268): every value consumed at render time is exposed and effectful in the
#   configuration view, for every widget and wallpaper. A literal no key reaches must say
#   what it is (STATE, MOUNT, WITHHELD with a reason) or be recorded as OPEN debt.
package el.render_constants

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "C0: no templates were measured; the population is empty, not the widgets configurable"
}

# a property is judged: a key reaches it, or a disposition says what it is
configurable(p) if p.configurable == true

kind(p) := split(p.disposition, ":")[0] if is_string(object.get(p, "disposition", null))

known_kinds := {"STATE", "MOUNT", "WITHHELD", "OPEN"}

# METADATA
# title: "C1 — a literal render property no key reaches and nobody has classified"
deny contains msg if {
	some c in input.cases
	some p in c.props
	not configurable(p)
	object.get(p, "disposition", null) == null
	msg := sprintf("C1: %s:%d %s = %s is a render value no setting reaches and no disposition names", [c.template, p.line, p.name, p.literal])
}

# METADATA
# title: "C2 — a disposition names a kind this policy does not know, or gives no reason"
deny contains msg if {
	some c in input.cases
	some p in c.props
	not configurable(p)
	is_string(object.get(p, "disposition", null))
	not kind(p) in known_kinds
	msg := sprintf("C2: %s %s: disposition %q is not STATE, MOUNT, WITHHELD:<reason> or OPEN:<waypoint>", [c.template, p.name, p.disposition])
}

deny contains msg if {
	some c in input.cases
	some p in c.props
	not configurable(p)
	kind(p) in {"WITHHELD", "OPEN"}
	count(split(p.disposition, ":")) < 2
	msg := sprintf("C2: %s %s: %s needs a reason or a waypoint after the colon", [c.template, p.name, kind(p)])
}

# METADATA
# title: "C3 — a registry entry that names no property is stale"
deny contains msg if {
	some entry in object.get(input, "registry_stale", [])
	msg := sprintf("C3: render-constants.json names %s, which no template declares as a literal property", [entry])
}

# METADATA
# title: "O — an OPEN disposition is debt: counted and printed, never a pass"
withheld contains msg if {
	some c in input.cases
	some p in c.props
	not configurable(p)
	kind(p) == "OPEN"
	msg := sprintf("O: %s %s is OPEN (%s): a render value that should be a setting and is not yet", [c.template, p.name, p.disposition])
}

withheld contains msg if {
	not is_array(object.get(input, "registry_stale", null))
	msg := "O: registry_stale was not measured"
}

admitted contains sprintf("%s:%s", [c.template, p.name]) if {
	some c in input.cases
	some p in c.props
	configurable(p)
}

admitted contains sprintf("%s:%s", [c.template, p.name]) if {
	some c in input.cases
	some p in c.props
	not configurable(p)
	kind(p) in {"STATE", "MOUNT"}
}

admitted contains sprintf("%s:%s", [c.template, p.name]) if {
	some c in input.cases
	some p in c.props
	not configurable(p)
	kind(p) == "WITHHELD"
	count(split(p.disposition, ":")) >= 2
}
