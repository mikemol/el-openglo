package el.plugin_ids_test

import data.el.plugin_ids as p
import rego.v1

live := {"id": "org.el.openglo.live", "kind": "plasma/wallpapers", "dir": "org.el.openglo.live", "dir_matches": true}

lnf := {"id": "org.el.openglo.elamber", "kind": "plasma/look-and-feel", "dir": "org.el.openglo.elamber", "dir_matches": true}

good := {"shipped": [live, lnf], "referenced": [
	{"id": "org.el.openglo.live", "file": "/x/layout.js", "prefix": false},
	{"id": "org.el.openglo", "file": "/usr/bin/el-openglo-apply", "prefix": true},
], "withheld": null}

test_admits_a_consistent_install if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
}

test_p0_refuses_an_absent_population if {
	"P0: no shipped package was measured; the stage or the walk is broken" in p.deny with input as {}
}

test_p1_refuses_an_id_that_is_not_its_directory if {
	bad := object.union(live, {"id": "org.el.renamed", "dir_matches": false})
	"P1: plasma/wallpapers/org.el.openglo.live declares Id org.el.renamed, not its directory name" in p.deny with input as object.union(good, {"shipped": [bad, lnf]})
}

# the f521e6f shape: a desktop still naming a per-variant wallpaper the build dropped
test_p2_refuses_a_dangling_reference if {
	inp := object.union(good, {"referenced": [{"id": "org.el.openglo.live.elazure", "file": "/x/appletsrc", "prefix": false}]})
	"P2: /x/appletsrc references org.el.openglo.live.elazure, which no shipped package declares" in p.deny with input as inp
}

test_p2_refuses_a_prefix_nothing_extends if {
	inp := object.union(good, {"referenced": [{"id": "org.el.nothing", "file": "/usr/bin/x", "prefix": true}]})
	"P2: /usr/bin/x references org.el.nothing.* (a run-time prefix), which no shipped package declares" in p.deny with input as inp
}

test_p2_a_prefix_is_not_satisfied_by_its_own_exact_id_alone if {
	only := {"id": "org.el.solo", "kind": "plasma/plasmoids", "dir": "org.el.solo", "dir_matches": true}
	inp := {"shipped": [only], "referenced": [{"id": "org.el.solo", "file": "/usr/bin/x", "prefix": true}], "withheld": null}
	some m in p.deny with input as inp
	startswith(m, "P2: /usr/bin/x references org.el.solo.*")
}

test_p3_withholds_a_reference_whose_prefix_was_not_measured if {
	inp := object.union(good, {"referenced": [{"id": "org.el.x", "file": "/y", "prefix": null}]})
	"P3: org.el.x in /y: whether it is a prefix was not measured" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
}

test_p3_withholds_an_unstaged_tree if {
	inp := {"shipped": [], "referenced": [], "withheld": "not a staged install tree"}
	"P3: not a staged install tree" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
}
