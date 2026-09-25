package el.migration_test

import data.el.migration as p
import rego.v1

marquee := {"type": "org.el.notifymarquee", "config": {"hoverPause": "false"}, "geometry": [300, 0, 420, 30]}

landed := {
	"runner": true,
	"desktops": [{"wallpaper": "org.el.openglo.live"}],
	"panels": [{"widgets": [
		{"type": "org.kde.plasma.kickoff", "config": {}, "geometry": [0, 0, 30, 30]},
		{"type": "org.el.segclock", "config": {}, "geometry": [800, 0, 120, 30]},
		marquee,
	]}],
}

with_widgets(ws) := object.union(landed, {"panels": [{"widgets": ws}]})

test_admits_a_landed_migration if {
	count(p.deny) == 0 with input as landed
	count(p.withheld) == 0 with input as landed
	p.admitted == {"migration"} with input as landed
}

test_withholds_without_the_runner if {
	inp := {"runner": false, "why": "/usr/bin/qml not present"}
	some m in p.withheld with input as inp
	startswith(m, "G0: the qml runner is not on this host")
	count(p.deny) == 0 with input as inp
	count(p.admitted) == 0 with input as inp
}

test_withholds_an_absent_runner_fact if {
	"G0: runner was not measured" in p.withheld with input as {}
	count(p.admitted) == 0 with input as {}
}

test_g0_refuses_an_empty_shell if {
	inp := {"runner": true, "desktops": [], "panels": []}
	"G0: the shell reported no desktop; the harness measured nothing" in p.deny with input as inp
	"G0: the shell reported no panel widgets; the harness measured nothing" in p.deny with input as inp
	count(p.admitted) == 0 with input as inp
}

# the selftest's old fixture: an untouched desktop
test_g1_refuses_a_legacy_wallpaper if {
	inp := object.union(landed, {"desktops": [{"wallpaper": "org.el.openglo.live.elazure"}]})
	"G1: a desktop's wallpaper is org.el.openglo.live.elazure, not org.el.openglo.live" in p.deny with input as inp
}

test_g2_refuses_a_surviving_legacy_applet if {
	ws := array.concat(landed.panels[0].widgets, [{"type": "org.el.segclock.elazure", "config": {}, "geometry": [0, 0, 1, 1]}])
	"G2: legacy applet org.el.segclock.elazure survived" in p.deny with input as with_widgets(ws)
}

test_g2_refuses_a_duplicated_applet if {
	ws := array.concat(landed.panels[0].widgets, [marquee])
	"G2: org.el.notifymarquee appears 2 times, not once" in p.deny with input as with_widgets(ws)
}

test_g2_refuses_a_missing_applet if {
	ws := [w | some w in landed.panels[0].widgets; w.type != "org.el.segclock"]
	"G2: org.el.segclock appears 0 times, not once" in p.deny with input as with_widgets(ws)
}

test_g3_refuses_a_lost_stock_widget if {
	ws := [w | some w in landed.panels[0].widgets; w.type != "org.kde.plasma.kickoff"]
	"G3: a stock widget was lost (org.kde.plasma.kickoff)" in p.deny with input as with_widgets(ws)
}

test_g4_refuses_dropped_settings if {
	# built whole: object.union MERGES nested objects, so {"config": {}} would keep hoverPause
	moved := {"type": "org.el.notifymarquee", "config": {}, "geometry": [300, 0, 420, 30]}
	ws := [w | some w in landed.panels[0].widgets; w.type != "org.el.notifymarquee"]
	"G4: the marquee's settings were not carried (hoverPause=null)" in p.deny with input as with_widgets(array.concat(ws, [moved]))
}

test_g4_refuses_a_moved_marquee if {
	moved := object.union(marquee, {"geometry": [0, 0, 420, 30]})
	ws := [w | some w in landed.panels[0].widgets; w.type != "org.el.notifymarquee"]
	some m in p.deny with input as with_widgets(array.concat(ws, [moved]))
	startswith(m, "G4: the marquee moved")
}
