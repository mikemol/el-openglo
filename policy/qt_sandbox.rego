# METADATA
# title: "Q0 — an empty population admits nothing"
# description: |
#   The measurement is `scripts/check_qt_sandbox.py --json`: every spawn in the
#   tree whose argv[0] resolves to a Qt tool, plus every qt_sandbox.run call.
#   W73: an unsandboxed qml harness reached the operator's display and NVIDIA
#   driver, crashed, dumped core and raised a desktop crash notification.
package el.qt_sandbox

import rego.v1

import data.el.truth

cases := object.get(input, "cases", [])

deny contains msg if {
	count(cases) == 0
	msg := "Q0: no Qt spawn site was measured; the search is broken, not the tree clean"
}

measured contains c if {
	some c in cases
	not c.withheld
}

# Q1 — a Qt tool is spawned only through qt_sandbox.run
deny contains msg if {
	some c in measured
	not c.routed
	msg := sprintf("Q1: %s spawns %v via %v, not qt_sandbox.run — it can reach the session, the GPU and the crash handler", [c.id, c.tool, c.via])
}

# the sites that ask for the GPU scene graph: not denied (the operator decides,
# and qt_sandbox grants it only under EL_QT_GPU=1), but listed
gpu_sites contains c.id if {
	some c in measured
	truth.py(c.routed)
	c.gpu != false
}

admitted contains c.id if {
	some c in measured
	truth.py(c.routed)
}

withheld contains msg if {
	some c in cases
	truth.py(c.withheld)
	msg := sprintf("%s: %s", [c.id, c.withheld])
}
