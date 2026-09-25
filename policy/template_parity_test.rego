package el.template_parity_test

import data.el.template_parity as p
import rego.v1

pair(id) := {"id": id, "baseline": "x.qml", "baseline_present": true, "links": 1, "skip": null, "raised": null, "equal": true, "got_bytes": 100, "want_bytes": 100}

good := {"cases": [pair("make_clock.main_qml"), pair("make_taskswitch.main_qml")]}

test_admits_faithful_templates if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	p.admitted == {"make_clock.main_qml", "make_taskswitch.main_qml"} with input as good
}

test_t0_refuses_no_pairs if {
	some m in p.deny with input as {}
	startswith(m, "T0:")
}

test_t1_refuses_a_missing_baseline if {
	c := object.union(pair("make_clock.main_qml"), {"baseline_present": false, "links": null, "equal": null})
	some m in p.deny with input as {"cases": [c]}
	startswith(m, "T1: make_clock.main_qml: NO BASELINE")
	count(p.admitted) == 0 with input as {"cases": [c]}
}

# the dedup-pass defect: a baseline hard-linked to the template it certifies
test_t2_refuses_a_shared_inode if {
	c := object.union(pair("make_clock.config_qml"), {"links": 8})
	some m in p.deny with input as {"cases": [c]}
	startswith(m, "T2: make_clock.config_qml: SHARED INODE (x.qml: 8 links)")
	count(p.admitted) == 0 with input as {"cases": [c]}
}

test_t3_refuses_a_raising_generator if {
	c := object.union(pair("make_clock.main_qml"), {"raised": "FileNotFoundError: make_wallpaper.py", "equal": null})
	"T3: make_clock.main_qml: RAISED FileNotFoundError: make_wallpaper.py" in p.deny with input as {"cases": [c]}
}

test_t3_refuses_a_difference if {
	c := object.union(pair("make_notify_marquee.main_qml"), {"equal": false, "got_bytes": 42963, "want_bytes": 40302})
	some m in p.deny with input as {"cases": [c]}
	startswith(m, "T3: make_notify_marquee.main_qml: DIFFERS (42963 vs 40302 bytes)")
}

# a skip beside faithful pairs is a counted SKIP, not a pass of that pair
test_t3_withholds_a_skipped_pair if {
	s := object.union(pair("make_notify_marquee.main_qml"), {"skip": "PARITY_FONT = /x.ttf is not on this host", "equal": null})
	inp := {"cases": [pair("make_clock.main_qml"), s]}
	"T3: make_notify_marquee.main_qml: SKIP (PARITY_FONT = /x.ttf is not on this host)" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
	p.admitted == {"make_clock.main_qml"} with input as inp
}

# the old silent pass: every pair skipped printed "0 of N ... SKIPPED" and exited 0
test_all_skipped_admits_nothing if {
	s := object.union(pair("make_notify_marquee.main_qml"), {"skip": "font absent", "equal": null})
	count(p.admitted) == 0 with input as {"cases": [s]}
	count(p.withheld) == 1 with input as {"cases": [s]}
}

test_all_null_case_withheld_only if {
	c := {"id": "make_clock.main_qml", "baseline": "x.qml", "baseline_present": true, "links": 1, "skip": null, "raised": null, "equal": null, "got_bytes": null, "want_bytes": null}
	"W: make_clock.main_qml: equal was not measured" in p.withheld with input as {"cases": [c]}
	count(p.deny) == 0 with input as {"cases": [c]}
	count(p.admitted) == 0 with input as {"cases": [c]}
}
