# METADATA
# title: "C0 — no declared emitter measured admits nothing"
# description: |
#   The measurement is `scripts/check_token_source.py --json`: every colour
#   emitter DECLARED in emitters.ROLES, whether its file is present, and which
#   palette authorities it reads (make_preview.parse_scheme, make_schemes.GRID —
#   directly, or `via` a sibling emitter); plus the roster drift. The roster is
#   declared, not discovered: a discovered population cannot tell a clean tree
#   from a deleted one.
package el.token_source

import rego.v1

import data.el.truth

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "C0: no emitters were measured; the search is broken, not the tree clean"
}

# METADATA
# title: "C1 — the tree and emitters.ROLES agree"
# description: |
#   A SHRINKING POPULATION IS NOT A PASSING ONE. Remove make_css.py and a
#   discovered roster reported "15 of 15" and exited 0 (W65). A generator in the
#   tree with no role is one no gate ranges over — make_wallpaper computed its
#   own colours for months and was found on this check's first run.
deny contains msg if {
	some f in input.undeclared
	msg := sprintf("C1: %s is in the tree without a role in emitters.ROLES (%d declared)", [f, input.declared])
}

deny contains msg if {
	some f in input.absent
	msg := sprintf("C1: %s is declared in emitters.ROLES and not in the tree", [f])
}

deny contains msg if {
	some c in input.cases
	c.present == false
	msg := sprintf("C1: %s is a declared emitter whose file is absent", [c.file])
}

# METADATA
# title: "W — an emitter whose presence or reads were not reported is withheld"
# description: |
#   check_token_source always emits `present` (bool) and `reads` (list) per
#   case. Null or absent means the measurement could not say: not judged.
withheld contains msg if {
	some c in input.cases
	not is_boolean(object.get(c, "present", null))
	msg := sprintf("%s: present was not measured", [c.file])
}

withheld contains msg if {
	some c in input.cases
	truth.py(c.present)
	not is_array(object.get(c, "reads", null))
	msg := sprintf("%s: reads was not measured", [c.file])
}

# METADATA
# title: "C2 — every emitter reads a palette authority"
# description: |
#   The witness is SOURCES FROM, not CONTAINS NO HEX: a generator may mention
#   hexes (a fallback, a mask, pure black); what drifts is a target that
#   computes its palette independently of the one every other target reads.
deny contains msg if {
	some c in input.cases
	truth.py(c.present)
	count(c.reads) == 0
	msg := sprintf("C2: %s reads no palette authority (%s); a target that computes its own colours can drift from every other target", [c.file, concat(", ", object.get(input, "authorities", []))])
}

admitted contains c.file if {
	some c in input.cases
	truth.py(c.present)
	count(c.reads) > 0
}
