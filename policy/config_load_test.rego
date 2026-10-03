package el.config_load_test

import data.el.config_load as c
import rego.v1

clean := {"page": "clock-config.qml", "unplaced": 0, "load_status": 1, "other_stderr": []}

hit := {"page": "marquee-config.qml", "unplaced": 2, "load_status": 1, "other_stderr": []}

test_admits_clean_when_control_provokes if {
	inp := {"control_provokes_unplaced": true, "pages": [clean]}
	count(c.deny) == 0 with input as inp
	c.admitted == {"clock-config.qml"} with input as inp
	count(c.withheld) == 0 with input as inp
}

test_clean_without_a_provoking_control_is_withheld_not_admitted if {
	inp := {"control_provokes_unplaced": false, "pages": [clean]}
	count(c.deny) == 0 with input as inp
	count(c.admitted) == 0 with input as inp
	count(c.withheld) == 1 with input as inp
}

test_unmeasured_control_is_withheld if {
	inp := {"control_provokes_unplaced": null, "pages": [clean]}
	count(c.admitted) == 0 with input as inp
	count(c.withheld) == 1 with input as inp
}

test_l2_refuses_the_line if {
	inp := {"control_provokes_unplaced": true, "pages": [clean, hit]}
	"L2: marquee-config.qml shows the unplaced-graphics-object line 2 time(s)" in c.deny with input as inp
	not "marquee-config.qml" in c.admitted with input as inp
}

test_l2_refuses_even_without_a_control if {
	inp := {"control_provokes_unplaced": false, "pages": [hit]}
	some m in c.deny with input as inp
	startswith(m, "L2:")
}

test_l1_refuses_a_page_not_ready if {
	inp := {"control_provokes_unplaced": true, "pages": [object.union(clean, {"load_status": 3})]}
	some m in c.deny with input as inp
	startswith(m, "L1:")
	count(c.admitted) == 0 with input as inp
}

test_l0_refuses_absent_population if {
	some m in c.deny with input as {}
	startswith(m, "L0:")
}

test_l0_refuses_empty_population if {
	some m in c.deny with input as {"pages": []}
	startswith(m, "L0:")
}

test_withheld_only if {
	inp := {"control_provokes_unplaced": null, "pages": [{"page": "clock-config.qml", "withheld": "OSError: no kwin"}]}
	count(c.deny) == 0 with input as inp
	count(c.withheld) == 1 with input as inp
	count(c.admitted) == 0 with input as inp
}
