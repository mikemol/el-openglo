# METADATA
# title: "C0 — an empty codomain admits nothing"
# description: |
#   The measurement is `scripts/check_codomain.py --json` (W42): the emitted half
#   read from check_publishing, the gaps from catalog/codomain.json. No emitted
#   surface means the roster read broke, not that nothing ships.
package el.codomain

import rego.v1

import data.el.truth

emitted := object.get(input, "emitted", [])

gaps := object.get(input, "gaps", [])

deny contains "C0: no emitted surface was measured; the roster read is broken" if {
	count(emitted) == 0
}

# METADATA
# title: "C1 — every gap states its contract, venue, licence, reach and cost"
# description: |
#   A gap with no contract is a wish, not a census row: the contract is what an
#   emitter for it must satisfy, and reach/cost are what rank it.
deny contains msg if {
	some g in gaps
	count(object.get(g, "missing", [])) > 0
	msg := sprintf("C1: gap %v lacks %v", [object.get(g, "target", null), g.missing])
}

# METADATA
# title: "C2 — a gap is not already emitted"
# description: |
#   A gap whose target an emitter already writes is stale: the map would rank
#   work that is done.
emitted_targets := {e.target | some e in emitted}

deny contains msg if {
	some g in gaps
	g.target in emitted_targets
	msg := sprintf("C2: gap %v is already emitted (make_%v)", [g.target, g.target])
}

withheld contains msg if {
	truth.py(object.get(input, "gaps_withheld", null))
	msg := sprintf("C3: the gaps file was not read: %v", [input.gaps_withheld])
}
