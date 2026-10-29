package el.config_reach_shards_test

import rego.v1

import data.el.config_reach_shards

shards := [["clock", "wallpaper"], ["marquee"]]

both := [
	{"key": "CONFIG-REACH", "operands": ["clock", "wallpaper"]},
	{"key": "CONFIG-REACH-MARQUEE", "operands": ["marquee"]},
]

test_absent_population_denied if {
	"S0: no shard of @CONFIG-REACH was declared" in config_reach_shards.deny with input as {}
}

test_every_shard_warranted_admitted if {
	count(config_reach_shards.deny) == 0 with input as {"shards": shards, "warrants": both}
}

test_dropped_warrant_denied if {
	some m in config_reach_shards.deny with input as {"shards": shards, "warrants": [both[0]]}
	startswith(m, "S1: shard [\"marquee\"]")
}

test_drifted_operands_denied_both_ways if {
	drifted := [both[0], {"key": "CONFIG-REACH-MARQUEE", "operands": ["marquee", "clock"]}]
	msgs := config_reach_shards.deny with input as {"shards": shards, "warrants": drifted}
	some a in msgs
	startswith(a, "S1: shard [\"marquee\"]")
	some b in msgs
	startswith(b, "S2: @CONFIG-REACH-MARQUEE")
}

test_whole_registry_warrant_denied if {
	whole := [{"key": "CONFIG-REACH", "operands": []}]
	some m in config_reach_shards.deny with input as {"shards": shards, "warrants": whole}
	startswith(m, "S2: @CONFIG-REACH runs []")
}

test_unreadable_bib_is_withheld_not_denied if {
	i := {"shards": shards, "warrants": [], "withheld": ["paperkit is not importable"]}
	count(config_reach_shards.deny) == 0 with input as i
	count(config_reach_shards.withheld) == 1 with input as i
}
