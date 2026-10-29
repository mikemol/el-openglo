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

# METADATA
# title: "T2 — a kept cache directory is not bounded (W787)"
# description: |
#   The shared staged-tree cache persists on purpose, so it is not a T1 leak, but a cache keyed per
#   tree digest grows with every edit unless it prunes. It may hold at most `cache_keep` stage-*
#   trees and no .part-* leftover of a staging that died.
deny contains msg if {
	some c in object.get(input, "cases", [])
	some dir, entries in object.get(c, "persistent", {})
	n := count([e | some e in entries; startswith(e, "stage-")])
	n > object.get(input, "cache_keep", 2)
	msg := sprintf("T2: %s kept %d trees in %s, over the bound %d", [c.subject, n, dir, object.get(input, "cache_keep", 2)])
}

deny contains msg if {
	some c in object.get(input, "cases", [])
	some dir, entries in object.get(c, "persistent", {})
	some e in entries
	startswith(e, ".part-")
	msg := sprintf("T2: %s left a partial staging %s in %s", [c.subject, e, dir])
}

withheld contains msg if {
	some w in object.get(input, "withheld", [])
	msg := sprintf("T0: not measured: %s", [w])
}

admitted contains c.subject if {
	some c in object.get(input, "cases", [])
	count(object.get(c, "leaked", [])) == 0
}
