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

# null is truthy to a bare Rego reference: a null routed is not routed, and a
# null withheld is not a withholding
test_null_routed_withheld_does_not_fire if {
	inp := {"cases": [routed, object.union(bare, {"routed": null, "withheld": null})]}
	not "scripts/check_ebuild.py:9" in q.admitted with input as inp
	# was count(withheld) == 0 — the silently-nothing exactly-once forbids; a null
	# withheld is still no REASON, but the null routed is now withheld by name
	q.withheld == {"scripts/check_ebuild.py:9: routed was not measured"} with input as inp
}

test_all_null_case_withheld_only if {
	inp := {"cases": [routed, {"id": "scripts/x.py:3", "file": null, "line": null, "tool": null, "via": null, "routed": null, "gpu": null, "withheld": null}]}
	q.withheld == {"scripts/x.py:3: routed was not measured"} with input as inp
	not "scripts/x.py:3" in q.admitted with input as inp
	d := q.deny with input as inp
	every m in d { not contains(m, "scripts/x.py:3") }
}

# N1 fix (line 23): HEAD's `not c.withheld` read a null reason as a withholding,
# so an unrouted site with withheld: null was never denied
test_null_withheld_unrouted_is_denied if {
	inp := {"cases": [object.union(bare, {"withheld": null})]}
	some m in q.deny with input as inp
	startswith(m, "Q1: scripts/check_ebuild.py:9")
}

# N1 fix (line 29): HEAD's `not c.routed` read a null routed as routed
test_null_routed_is_withheld if {
	inp := {"cases": [object.union(bare, {"routed": null})]}
	"scripts/check_ebuild.py:9: routed was not measured" in q.withheld with input as inp
}

test_withheld_only if {
	inp := {"cases": [{"id": "broken.py", "withheld": "SyntaxError"}]}
	count(q.deny) == 0 with input as inp
	count(q.withheld) == 1 with input as inp
	count(q.admitted) == 0 with input as inp
}
