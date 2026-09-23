package el.qt_sandbox_test

import data.el.qt_sandbox as q
import rego.v1

routed := {"id": "theme_probe.py:75", "file": "theme_probe.py", "line": 75, "tool": "qml", "via": "qt_sandbox", "routed": true, "gpu": false}

gpu := {"id": "scripts/render_qml.py:327", "file": "scripts/render_qml.py", "line": 327, "tool": "qml", "via": "qt_sandbox", "routed": true, "gpu": "conditional: gpu"}

bare := {"id": "scripts/check_ebuild.py:9", "file": "scripts/check_ebuild.py", "line": 9, "tool": "qml", "via": "subprocess", "routed": false, "gpu": null}

test_admits_routed if {
	inp := {"cases": [routed, gpu]}
	count(q.deny) == 0 with input as inp
	q.admitted == {"theme_probe.py:75", "scripts/render_qml.py:327"} with input as inp
	q.gpu_sites == {"scripts/render_qml.py:327"} with input as inp
}

test_q0_refuses_absent_population if {
	some msg in q.deny with input as {}
	startswith(msg, "Q0:")
}

test_q0_refuses_empty_population if {
	some msg in q.deny with input as {"cases": []}
	startswith(msg, "Q0:")
}

test_q1_refuses_unrouted if {
	some msg in q.deny with input as {"cases": [routed, bare]}
	startswith(msg, "Q1: scripts/check_ebuild.py:9")
}

test_unrouted_is_not_admitted if {
	not "scripts/check_ebuild.py:9" in q.admitted with input as {"cases": [bare]}
}

test_withheld_only if {
	inp := {"cases": [{"id": "broken.py", "withheld": "SyntaxError"}]}
	count(q.deny) == 0 with input as inp
	count(q.withheld) == 1 with input as inp
	count(q.admitted) == 0 with input as inp
}
