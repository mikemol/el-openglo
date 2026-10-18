package el.qml_target_test

import data.el.qml_target as p
import rego.v1

ok_plasmoid := {"id": "org.el.segclock", "kind": "plasmoid", "entry": "main.qml", "state": "ok"}

tabbox := {"id": "org.el.taskswitch", "kind": "tabbox", "entry": "main.qml", "state": "ok"}

test_admits_packages_that_load if {
	inp := {"cases": [ok_plasmoid, tabbox]}
	count(p.deny) == 0 with input as inp
	count(p.withheld) == 0 with input as inp
	p.admitted == {"org.el.segclock", "org.el.taskswitch"} with input as inp
}

test_q0_refuses_an_absent_population if {
	"Q0: no staged QML package was measured; the stage is broken, not the tree clean" in p.deny with input as {}
}

# the 2026-09-26 failure: `var byte` read as a lint error under the laptop's Qt
test_q1_refuses_a_package_that_fails_to_load if {
	bad := {"id": "org.el.metrics", "kind": "plasmoid", "entry": "main.qml", "state": "refused", "step": "lint"}
	inp := {"cases": [ok_plasmoid, bad]}
	"Q1: org.el.metrics (plasmoid) fails under the operator's Qt at step lint" in p.deny with input as inp
	not "org.el.metrics" in p.admitted with input as inp
}

test_q2_refuses_a_package_with_no_verdict_and_no_reason if {
	silent := {"id": "org.el.x", "kind": "wallpaper", "entry": "main.qml"}
	"Q2: org.el.x (wallpaper) carries neither a verdict nor a reason it has none" in p.deny with input as {"cases": [silent]}
}

# a runner that could not run is a fact about the machine: withheld beside the admitted package
test_q3_withholds_a_package_the_runner_could_not_measure if {
	w := {"id": "org.el.taskswitch", "kind": "tabbox", "entry": "main.qml", "withheld": "qml_check could not run (exit 2)"}
	inp := {"cases": [ok_plasmoid, w]}
	count(p.deny) == 0 with input as inp
	p.admitted == {"org.el.segclock"} with input as inp
	some m in p.withheld with input as inp
	startswith(m, "Q3: org.el.taskswitch (tabbox) was not measured")
}

test_q3_withheld_alone_admits_nothing if {
	w := {"id": "a", "kind": "sddm", "entry": "Main.qml", "withheld": "sg is not installed"}
	count(p.admitted) == 0 with input as {"cases": [w]}
	count(p.deny) == 0 with input as {"cases": [w]}
}
