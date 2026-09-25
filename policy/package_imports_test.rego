package el.package_imports_test

import data.el.package_imports as p
import rego.v1

pkg(name) := {"package": name, "files": ["main.qml", "metadata.json"], "documents": ["main.qml"], "missing": []}

good := {"packages": [pkg("org.el.segclock"), pkg("org.el.openglo.live")]}

test_admits_packages_whose_types_resolve if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	p.admitted == {"org.el.segclock", "org.el.openglo.live"} with input as good
}

test_p0_refuses_no_packages if {
	some m in p.deny with input as {}
	startswith(m, "P0:")
}

# the live defect of s134: the mount shipped without the display it instantiates
test_p2_refuses_an_unresolved_type if {
	broken := object.union(pkg("org.el.openglo.live"), {"missing": [{"type": "SegmentChar", "file": "main.qml", "line": 105}]})
	inp := {"packages": [broken]}
	"P2: org.el.openglo.live: SegmentChar at main.qml:105 is not in the package — it would fail to load" in p.deny with input as inp
	count(p.admitted) == 0 with input as inp
}

# the vacuous pass: no documents means no unresolved types
test_p1_refuses_a_package_with_no_documents if {
	empty := object.union(pkg("org.el.notifymarquee"), {"documents": []})
	"P1: org.el.notifymarquee: no QML document under contents/ui; nothing was linted" in p.deny with input as {"packages": [empty]}
}

test_withholds_without_qmllint if {
	held := {"package": "org.el.segclock", "withheld": "/usr/lib64/qt6/bin/qmllint is not on this host"}
	inp := {"packages": [held]}
	"P0: org.el.segclock: /usr/lib64/qt6/bin/qmllint is not on this host" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
	count(p.admitted) == 0 with input as inp
}

test_all_null_package_withheld_only if {
	inp := {"packages": [{"package": "org.el.segclock", "files": null, "documents": null, "missing": null}]}
	"W: org.el.segclock: documents was not measured" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
	count(p.admitted) == 0 with input as inp
}
