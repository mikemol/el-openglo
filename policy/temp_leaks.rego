# METADATA
# title: "T0 — no subject's temp leftovers were measured"
# description: |
#   The measurement is `scripts/check_temp_leaks.py --json`: each listed subject run in its own
#   subprocess with a private TMPDIR, and what is left there once it has exited. An empty
#   population is a broken run, not a clean temp dir.
# custom:
#   family: gate
package el.temp_leaks

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "T0: no subject's temp leftovers were measured"
}

# METADATA
# title: "T1 — a subject leaves a temp directory behind (W784)"
# description: |
#   github-42 found 12018 leaked el-openglo-lnf-* directories in /var/tmp: one `mkdtemp` that ran
#   at import in every process that imported make_deb. The host's zram mount behind /tmp and
#   /var/tmp filled and went emergency read-only. A subject must remove what it creates on every
#   exit path.
deny contains msg if {
	some c in object.get(input, "cases", [])
	count(object.get(c, "leaked", [])) > 0
	msg := sprintf("T1: %s left %d temp entr(ies): %v", [c.subject, count(c.leaked), c.leaked])
}

withheld contains msg if {
	some w in object.get(input, "withheld", [])
	msg := sprintf("T0: not measured: %s", [w])
}

admitted contains c.subject if {
	some c in object.get(input, "cases", [])
	count(object.get(c, "leaked", [])) == 0
}
