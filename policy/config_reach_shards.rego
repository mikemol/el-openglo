# METADATA
# title: "S0 — no shard of @CONFIG-REACH was declared"
# description: |
#   The measurement is `scripts/check_config_reach_shards.py --json`: the SHARDS of
#   scripts/check_config_reach.py (an exact partition of the mount registry) and the mount
#   operands of every warrant whose check is `opa_gate.py config_reach ...`. An empty
#   SHARDS is a broken read, not a registry with nothing to measure.
# custom:
#   family: gate
package el.config_reach_shards

import rego.v1

deny contains msg if {
	count(object.get(input, "shards", [])) == 0
	msg := "S0: no shard of @CONFIG-REACH was declared"
}

# METADATA
# title: "S1 — a shard no warrant runs exactly (W778)"
# description: |
#   A shard whose warrant was dropped, or whose operands drifted, leaves a slice of the
#   mount registry never measured while every remaining claim stays green over a smaller
#   population. A bib that could not be read is withheld, never read as "no warrant".
deny contains msg if {
	count(object.get(input, "withheld", [])) == 0
	some s in object.get(input, "shards", [])
	not warranted(s)
	msg := sprintf("S1: shard %v has no warrant running exactly it", [s])
}

# METADATA
# title: "S2 — a config_reach warrant that runs no declared shard (W778)"
# description: |
#   A warrant passing operands that are no shard (or none at all, the whole registry in
#   one claim, which W771 sharded to stay under paperkit's wall backstop) is measuring
#   something the declaration does not know about.
deny contains msg if {
	some w in object.get(input, "warrants", [])
	not w.operands in object.get(input, "shards", [])
	msg := sprintf("S2: @%s runs %v, which is no declared shard", [w.key, w.operands])
}

warranted(s) if {
	some w in object.get(input, "warrants", [])
	w.operands == s
}

withheld contains msg if {
	some m in object.get(input, "withheld", [])
	msg := sprintf("S0: not measured: %s", [m])
}
