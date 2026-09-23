# METADATA
# title: "A0 — a scan that found no write site measured nothing"
# description: |
#   The measurement is `scripts/check_atomic_writes.py --json`: every write site
#   (open for writing, write_text/bytes, shutil copies, path-taking savers,
#   svg2png write_to=) in every module emitters.ROLES declares. An empty
#   population is a broken search, not a clean tree.
package el.atomic_writes

import rego.v1

import data.el.truth

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "A0: no write site was measured"
}

# METADATA
# title: "A1 — every generator write is atomic, or exempt with a reason"
# description: |
#   W68: a truncate-then-write of a tracked output tore concurrent readers in the
#   parallel gate. A write goes through emitters.atomic_write / atomic_path, or
#   carries `# atomic-write: exempt — <reason>` at the site.
deny contains msg if {
	some c in object.get(input, "cases", [])
	not c.atomic
	not c.exempt
	msg := sprintf("A1: %s.py:%d %s is a plain write; route it through emitters.atomic_write/atomic_path", [c.module, c.line, c.kind])
}

deny contains msg if {
	some c in object.get(input, "cases", [])
	truth.py(c.exempt)
	trim_space(object.get(c, "reason", "")) == ""
	msg := sprintf("A2: %s.py:%d is exempt with no reason", [c.module, c.line])
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	not input.helper_present
	msg := "A3: emitters.atomic_write is absent — the admitted form names nothing"
}

withheld contains msg if {
	some u in object.get(input, "unreadable", [])
	msg := sprintf("A0: %s withheld: %s", [u.module, u.withheld])
}

admitted contains sprintf("%s.py:%d", [c.module, c.line]) if {
	some c in object.get(input, "cases", [])
	truth.py(c.atomic)
}

admitted contains sprintf("%s.py:%d", [c.module, c.line]) if {
	some c in object.get(input, "cases", [])
	truth.py(c.exempt)
	trim_space(object.get(c, "reason", "")) != ""
}
