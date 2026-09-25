# METADATA
# title: "G0 — the one-shot update ran against a populated fake shell"
# description: |
#   The measurement is `scripts/check_migration.py --json`: the fake Plasma shell
#   AFTER templates/one-theme-update.js ran under the qml runner — its desktops
#   (wallpaper plugin) and panels (each widget's type, config and geometry),
#   seeded like the operator's appletsrc of 2026-09-22 (a legacy wallpaper, a
#   legacy clock and marquee among stock widgets). `runner: false` when qml is
#   absent: withheld, nothing admitted. The script runs ONCE on real containments;
#   this is its only rehearsal. Weakness: the fake API is the subset the script
#   uses; a real Plasma API difference is invisible here.
package el.migration

import rego.v1

ONE_WALLPAPER := "org.el.openglo.live"

LEGACY := {"org.el.segclock.elazure", "org.el.notifymarquee.elazure"}

ONE_APPLETS := ["org.el.segclock", "org.el.notifymarquee"]

# the seeded marquee's placement and one of its non-default settings
MARQUEE_GEOMETRY := [300, 0, 420, 30]

withheld contains msg if {
	input.runner == false
	msg := sprintf("G0: the qml runner is not on this host (%v); the migration did not run", [object.get(input, "why", "")])
}

withheld contains "G0: runner was not measured" if {
	not is_boolean(object.get(input, "runner", null))
}

desktops := input.desktops if is_array(object.get(input, "desktops", null)) else := []

deny contains "G0: the shell reported no desktop; the harness measured nothing" if {
	input.runner == true
	count(desktops) == 0
}

deny contains "G0: the shell reported no panel widgets; the harness measured nothing" if {
	input.runner == true
	count(widgets) == 0
}

widgets := object.get(object.get(input, "panels", [{}])[0], "widgets", []) if {
	is_array(object.get(input, "panels", null))
	count(input.panels) > 0
} else := []

types := [w.type | some w in widgets]

# METADATA
# title: "G1 — every desktop's wallpaper is the one package id"
deny contains msg if {
	input.runner == true
	some d in desktops
	d.wallpaper != ONE_WALLPAPER
	msg := sprintf("G1: a desktop's wallpaper is %v, not %s", [d.wallpaper, ONE_WALLPAPER])
}

# METADATA
# title: "G2 — no legacy applet survives, and each one-id applet appears exactly once"
deny contains msg if {
	input.runner == true
	some t in types
	t in LEGACY
	msg := sprintf("G2: legacy applet %s survived", [t])
}

deny contains msg if {
	input.runner == true
	count(widgets) > 0
	some one in ONE_APPLETS
	n := count([t | some t in types; t == one])
	n != 1
	msg := sprintf("G2: %s appears %d times, not once", [one, n])
}

# METADATA
# title: "G3 — stock widgets are untouched"
deny contains "G3: a stock widget was lost (org.kde.plasma.kickoff)" if {
	input.runner == true
	count(widgets) > 0
	not "org.kde.plasma.kickoff" in types
}

# METADATA
# title: "G4 — the migrated marquee kept its settings and its place"
deny contains msg if {
	input.runner == true
	some w in widgets
	w.type == "org.el.notifymarquee"
	object.get(object.get(w, "config", {}), "hoverPause", null) != "false"
	msg := sprintf("G4: the marquee's settings were not carried (hoverPause=%v)", [object.get(object.get(w, "config", {}), "hoverPause", null)])
}

deny contains msg if {
	input.runner == true
	some w in widgets
	w.type == "org.el.notifymarquee"
	w.geometry != MARQUEE_GEOMETRY
	msg := sprintf("G4: the marquee moved: %v, not %v", [w.geometry, MARQUEE_GEOMETRY])
}

# one case: the migration. Admitted only when it ran, measured something, and nothing denies.
admitted contains "migration" if {
	input.runner == true
	count(deny) == 0
}
