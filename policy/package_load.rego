# METADATA
# title: "D0 — no loaded applet admits nothing"
# description: |
#   The measurement is `scripts/check_package_load.py --json` (W172): each shipped
#   applet loaded by plasmawindowed (Plasma's own applet host) from the staged
#   install tree, through qt_sandbox, read for a fixed window. Wallpapers are listed
#   under `not_loadable` (plasmawindowed hosts applets; a wallpaper needs a
#   containment) and are outside the population, never silently dropped.
package el.package_load

import rego.v1

import data.el.truth

cases := object.get(input, "cases", [])

deny contains "D0: no applet was loaded; the stage or the loader is broken" if {
	count(cases) == 0
	not truth.py(object.get(input, "withheld", null))
}

# METADATA
# title: "D1 — every shipped applet loads without a load error"
deny contains msg if {
	some c in cases
	some e in object.get(c, "errors", [])
	msg := sprintf("D1: %v failed to load: %v", [c.id, e])
}

# METADATA
# title: "D2 — a load run printed something"
# description: |
#   plasmawindowed always logs while it starts an applet; a run with no output at all
#   means the window closed before the loader ran or the loader never started, and a
#   clean verdict over it would be vacuous.
deny contains msg if {
	some c in cases
	object.get(c, "lines", null) == 0
	msg := sprintf("D2: %v produced no output; the load was not observed", [c.id])
}

admitted contains c.id if {
	some c in cases
	count(object.get(c, "errors", [])) == 0
	object.get(c, "lines", 0) > 0
}

withheld contains msg if {
	truth.py(object.get(input, "withheld", null))
	msg := sprintf("D3: %v", [input.withheld])
}
