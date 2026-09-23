# METADATA
# title: "Q0 — an empty population admits nothing"
# description: |
#   The measurement is `scripts/check_qt_sandbox.py --json`: every spawn in the
#   tree whose argv[0] resolves to a Qt tool, plus every qt_sandbox.run call.
#   W73: an unsandboxed qml harness reached the operator's display and NVIDIA
#   driver, crashed, dumped core and raised a desktop crash notification.
#
#   ⚑ EXACTLY ONCE: a case with a withholding reason (non-empty `withheld`) is
#   withheld; every other case always carries `routed` (bool). A null or absent
#   `routed` is a could-not-say — withheld by id, neither denied nor admitted.
package el.qt_sandbox

import rego.v1

import data.el.truth

cases := object.get(input, "cases", [])

deny contains msg if {
	count(cases) == 0
	msg := "Q0: no Qt spawn site was measured; the search is broken, not the tree clean"
}

# the site was parsed (a null / "" withheld is not a withholding reason)
measured contains c if {
	some c in cases
	not truth.py(object.get(c, "withheld", null))
}

# Q1 — a Qt tool is spawned only through qt_sandbox.run
deny contains msg if {
	some c in measured
	c.routed == false
	msg := sprintf("Q1: %s spawns %v via %v, not qt_sandbox.run — it can reach the session, the GPU and the crash handler", [c.id, c.tool, c.via])
}

# the sites that ask for the GPU scene graph: not denied (the operator decides,
# and qt_sandbox grants it only under EL_QT_GPU=1), but listed
gpu_sites contains c.id if {
	some c in measured
	c.routed == true
	c.gpu != false
}

admitted contains c.id if {
	some c in measured
	c.routed == true
}

withheld contains msg if {
	some c in cases
	truth.py(c.withheld)
	msg := sprintf("%s: %s", [c.id, c.withheld])
}

withheld contains msg if {
	some c in measured
	not is_boolean(object.get(c, "routed", null))
	msg := sprintf("%v: routed was not measured", [object.get(c, "id", null)])
}
