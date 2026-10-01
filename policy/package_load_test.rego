package el.package_load_test

import data.el.package_load as p
import rego.v1

clock := {"id": "org.el.segclock", "lines": 8, "errors": []}

marquee := {"id": "org.el.notifymarquee", "lines": 11, "errors": []}

good := {"cases": [clock, marquee], "not_loadable": ["org.el.openglo.live"], "withheld": null}

test_admits_clean_loads if {
	count(p.deny) == 0 with input as good
	p.admitted == {"org.el.segclock", "org.el.notifymarquee"} with input as good
}

test_d0_refuses_an_absent_population if {
	"D0: no applet was loaded; the stage or the loader is broken" in p.deny with input as {}
}

test_d1_refuses_a_load_error if {
	bad := object.union(clock, {"errors": ["main.qml:105:13: SegmentChar is not a type"]})
	"D1: org.el.segclock failed to load: main.qml:105:13: SegmentChar is not a type" in p.deny with input as object.union(good, {"cases": [bad, marquee]})
	not "org.el.segclock" in p.admitted with input as object.union(good, {"cases": [bad, marquee]})
}

test_d2_refuses_a_silent_run if {
	silent := object.union(clock, {"lines": 0})
	"D2: org.el.segclock produced no output; the load was not observed" in p.deny with input as object.union(good, {"cases": [silent]})
}

test_wallpapers_outside_the_population_never_deny if {
	count(p.deny) == 0 with input as object.union(good, {"not_loadable": ["a", "b", "c"]})
}

test_d3_withholds_a_machine_without_the_loader if {
	inp := {"cases": [], "not_loadable": [], "withheld": "/usr/bin/plasmawindowed is not installed"}
	"D3: /usr/bin/plasmawindowed is not installed" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
}
