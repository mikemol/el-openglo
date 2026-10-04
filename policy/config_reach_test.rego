package el.config_reach_test

import data.el.config_reach as p
import rego.v1

alive := {"key": "weight", "type": "Double", "low": 0.0, "high": 1.0, "differs": true, "inert": null}

dead := {"key": "weight", "type": "Double", "low": 0.0, "high": 1.0, "differs": false, "inert": null}

blink := {"key": "blinkColon", "type": "Bool", "low": false, "high": true, "differs": false, "inert": "one still holds the colon lit"}

good := {"cases": [alive, blink], "withheld": null}

test_admits_live_and_declared_inert_keys if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 2 with input as good
}

test_r0_refuses_an_empty_population if {
	some msg in p.deny with input as {"cases": [], "withheld": null}
	startswith(msg, "R0:")
}

test_r0_absent_population_is_empty if {
	some msg in p.deny with input as {}
	startswith(msg, "R0:")
}

# the failure the check exists for: a slider whose two ends draw the same picture
test_r1_refuses_a_dead_setting if {
	some msg in p.deny with input as {"cases": [alive, dead], "withheld": null}
	msg == "R1: clock/weight: rendering 0 and 1 gives the same picture; the setting does nothing"
}

test_r1_a_dead_setting_is_not_admitted if {
	not "clock/weight" in p.admitted with input as {"cases": [dead], "withheld": null}
}

# the same key can be alive on one mount and dead on another: the verdict is per mount
test_r1_is_per_mount if {
	wall_dead := object.union(dead, {"mount": "wallpaper"})
	inp := {"cases": [object.union(alive, {"mount": "clock"}), wall_dead], "withheld": null}
	some msg in p.deny with input as inp
	startswith(msg, "R1: wallpaper/weight:")
	"clock/weight" in p.admitted with input as inp
	not "wallpaper/weight" in p.admitted with input as inp
}

test_r2_refuses_an_inert_declaration_without_a_reason if {
	empty := object.union(blink, {"inert": ""})
	some msg in p.deny with input as {"cases": [alive, empty], "withheld": null}
	startswith(msg, "R2:")
}

# a mount the witness cannot render as one still is named debt, not a pass and not a denial
test_unmeasured_mount_is_named_debt if {
	inp := object.union(good, {"unmeasured": [{"mount": "marquee", "reason": "acts over time"}]})
	"U: marquee is not measured: acts over time" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
}

test_unmeasured_mount_without_a_reason_is_flagged if {
	inp := object.union(good, {"unmeasured": [{"mount": "marquee", "reason": ""}]})
	"U: marquee is unmeasured with no reason" in p.withheld with input as inp
}

# could not measure: withheld, never read as the settings alive or dead
test_withheld_when_the_runner_is_absent if {
	inp := {"cases": [], "withheld": "no qml runner"}
	"W: no qml runner" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
}

test_unmeasured_differs_is_withheld_not_judged if {
	inp := {"cases": [{"key": "bloom", "differs": null, "inert": null}], "withheld": null}
	"W: bloom: differs was not measured" in p.withheld with input as inp
	count([m | some m in p.deny with input as inp; startswith(m, "R1:")]) == 0
}
