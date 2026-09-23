# METADATA
# title: "A0 — a scan that found no write site measured nothing"
# description: |
#   The measurement is `scripts/check_atomic_writes.py --json`: every write site
#   (open for writing, write_text/bytes, shutil copies, path-taking savers,
#   svg2png write_to=) in every module emitters.ROLES declares. An empty
#   population is a broken search, not a clean tree.
package el.atomic_writes

import rego.v1

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
#
#   ⚑ EVERY SITE LANDS IN EXACTLY ONE OF withheld / deny / admitted.
#   check_atomic_writes.py ALWAYS emits `atomic` and `exempt` as booleans; a null
#   or absent one means the scan could not say, and the site is withheld (A4) —
#   never `not c.atomic`, which read null as "not atomic" and denied it. `reason`
#   is legitimately null on a non-exempt site, so it is read with a default.
deny contains msg if {
	some c in object.get(input, "cases", [])
	plain(c)
	msg := sprintf("A1: %s %v is a plain write; route it through emitters.atomic_write/atomic_path", [site(c), object.get(c, "kind", null)])
}

site(c) := sprintf("%v.py:%v", [object.get(c, "module", "?"), object.get(c, "line", "?")])

measured(c) if {
	is_boolean(object.get(c, "atomic", null))
	is_boolean(object.get(c, "exempt", null))
}

reasoned(c) if {
	r := object.get(c, "reason", null)
	is_string(r)
	trim_space(r) != ""
}

bare_exempt(c) if {
	measured(c)
	c.exempt == true
	not reasoned(c)
}

plain(c) if {
	measured(c)
	c.atomic == false
	c.exempt == false
}

deny contains msg if {
	some c in object.get(input, "cases", [])
	bare_exempt(c)
	msg := sprintf("A2: %s is exempt with no reason", [site(c)])
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	object.get(input, "helper_present", null) == false
	msg := "A3: emitters.atomic_write is absent — the admitted form names nothing"
}

# METADATA
# title: "A3w — a helper presence that was not measured is withheld"
withheld contains msg if {
	count(object.get(input, "cases", [])) > 0
	not is_boolean(object.get(input, "helper_present", null))
	msg := "A3: helper_present was not measured"
}

# METADATA
# title: "A4 — a site whose atomic / exempt was not measured is withheld"
withheld contains msg if {
	some c in object.get(input, "cases", [])
	not measured(c)
	msg := sprintf("A4: %s: atomic/exempt was not measured", [site(c)])
}

withheld contains msg if {
	some u in object.get(input, "unreadable", [])
	msg := sprintf("A0: %s withheld: %s", [u.module, u.withheld])
}

# admitted only while the helper is known present: with it absent every site is
# denied by A3, with it unmeasured nothing is judged
admitted contains site(c) if {
	object.get(input, "helper_present", null) == true
	some c in object.get(input, "cases", [])
	measured(c)
	not plain(c)
	not bare_exempt(c)
}
