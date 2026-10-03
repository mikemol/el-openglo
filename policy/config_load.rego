# METADATA
# title: "L0 — an empty population admits nothing"
# description: |
#   The measurement is `scripts/check_config_load.py --json` (W163): each emitted
#   config page loaded headless, its stderr read for plasmashell's `Created graphical
#   object was not placed in the graphics scene`, and a positive CONTROL (does this
#   host's harness provoke the line at all). L2 denies a page that shows the line; a
#   CLEAN page is admitted only when the control provokes it. A control that does not
#   makes every clean page WITHHELD (a counted SKIP: not reproduced is not absent).
package el.config_load

import rego.v1

pages := object.get(input, "pages", [])

deny contains msg if {
	count(pages) == 0
	msg := "L0: no config page was measured; the search is broken, not the tree clean"
}

measured contains p if {
	some p in pages
	not object.get(p, "withheld", false)
}

# L1 — a page that does not reach Ready did not run the test
deny contains msg if {
	some p in measured
	p.load_status != 1
	msg := sprintf("L1: %s did not load Ready (status %v)", [p.page, p.load_status])
}

# L2 — the line itself
deny contains msg if {
	some p in measured
	p.unplaced > 0
	msg := sprintf("L2: %s shows the unplaced-graphics-object line %d time(s)", [p.page, p.unplaced])
}

control_ok if input.control_provokes_unplaced == true

admitted contains p.page if {
	some p in measured
	p.load_status == 1
	p.unplaced == 0
	control_ok
}

withheld contains msg if {
	some p in pages
	reason := object.get(p, "withheld", false)
	reason != false
	msg := sprintf("%s: %s", [p.page, reason])
}

withheld contains msg if {
	some p in measured
	p.load_status == 1
	p.unplaced == 0
	not control_ok
	msg := sprintf("%s: loaded clean but the harness cannot provoke the line (control_provokes_unplaced=%v); clean is not confirmed", [p.page, object.get(input, "control_provokes_unplaced", null)])
}
