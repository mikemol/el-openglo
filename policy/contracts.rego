# METADATA
# title: "K0 - no surface measured admits nothing"
# description: |
#   W204. The measurement is `scripts/check_contracts.py --json`: per surface, the keys its
#   producer emits and the fields each consumer file reads. THE DECLARATION IS HERE: `declared`
#   lists the fields a surface always carries (`always`) and those it carries once the thing
#   exists (`when_exists`). A read outside the declaration, or a declared field the producer
#   does not emit, is denied. A surface whose producer or consumer could not be read is
#   withheld, never judged.
package el.contracts

import rego.v1

declared := {"render_screens.animation": {
	"always": {"file", "variant", "exists"},
	"when_exists": {
		"frames", "width", "axis", "pips", "floor", "shifts", "tears", "seamless",
		"fractional_share", "dominant_period", "dominant_line_share", "spectral_power",
		"period2_share", "logged_steps",
	},
}}

guaranteed(name) := object.get(declared, [name, "always"], set()) | object.get(declared, [name, "when_exists"], set())

surfaces := object.get(input, "surfaces", [])

deny contains msg if {
	count(surfaces) == 0
	msg := "K0: no surface was measured; the search is broken, not the contracts kept"
}

# METADATA
# title: "K1 - a surface that declares nothing has no contract"
deny contains msg if {
	some s in surfaces
	not s.surface in object.keys(declared)
	msg := sprintf("K1: %s has no declaration in policy/contracts.rego", [s.surface])
}

# METADATA
# title: "K2 - a consumer reads only fields the surface declares"
deny contains msg if {
	some s in surfaces
	s.surface in object.keys(declared)
	some c in s.consumers
	is_array(c.reads)
	some r in c.reads
	not r.field in guaranteed(s.surface)
	msg := sprintf("K2: %s:%d reads %s, which %s does not declare", [c.file, r.line, r.field, s.surface])
}

# METADATA
# title: "K3 - a producer emits every field it declares"
deny contains msg if {
	some s in surfaces
	s.surface in object.keys(declared)
	is_array(s.emitted)
	some f in guaranteed(s.surface)
	not f in s.emitted
	msg := sprintf("K3: %s declares %s but its producer does not emit it", [s.surface, f])
}

withheld contains msg if {
	some s in surfaces
	not is_array(object.get(s, "emitted", null))
	msg := sprintf("%s: the producer was not readable", [s.surface])
}

withheld contains msg if {
	some s in surfaces
	some c in object.get(s, "consumers", [])
	not is_array(object.get(c, "reads", null))
	msg := sprintf("%s: consumer %s was not readable", [s.surface, c.file])
}

# judged in full: declared, producer readable, every consumer readable
admitted contains s.surface if {
	some s in surfaces
	s.surface in object.keys(declared)
	is_array(s.emitted)
	every c in s.consumers {
		is_array(c.reads)
	}
	count(denied_surface(s.surface)) == 0
}

denied_surface(name) := {m |
	some m in deny
	contains(m, name)
}
