# METADATA
# title: "L0 — no measured declaration admits nothing"
# description: |
#   The measurement is `scripts/check_license.py --json`: every place the project
#   declares its licence (the emitters.LICENSE_SPDX authority, each generator's
#   metadata site, LICENSE / pyproject.toml / the ebuild, and every TRACKED emitted
#   file that declares one). An empty population is
#   a broken search, not a clean tree. Third-party licences are outside it.
package el.license

import rego.v1

import data.el.truth

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "L0: no licence declaration was measured"
}

# METADATA
# title: "L0 — every declaration kind is present"
# description: |
#   A kind with no case means its reader stopped answering (the constant was
#   renamed, the generators' sites moved to a shape the walker cannot see, the
#   LICENSE file vanished, git ls-files found no tracked emitted declaration);
#   the other kinds passing must not hide that. `emitted` is the tracked output
#   (metadata.json / .desktop) — the kind that would have caught W44's stale
#   plasma-clock metadata.json still saying GPLv3.
deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	some kind in {"authority", "generator", "file", "emitted"}
	count([c | some c in input.cases; c.kind == kind]) == 0
	msg := sprintf("L0: no %s declaration was measured", [kind])
}

# METADATA
# title: "L1 — every declaration is Apache-2.0"
# description: |
#   Operator, 2026-09-22 (W44): the project is Apache-2.0, not GPL-3. An id of
#   null is a declaration the measurement could not resolve — refused, since an
#   unreadable licence is not a correct one.
deny contains msg if {
	some c in input.cases
	c.id != "Apache-2.0"
	msg := sprintf("L1: %s declares %v, not Apache-2.0", [c.where, c.id])
}

# METADATA
# title: "L3 — the .deb ships a DEP-5 copyright file"
# description: |
#   A .deb carries /usr/share/doc/<pkg>/copyright. It is machine-readable DEP-5:
#   the Format header, `Files: *` under the authority's id (read from the
#   authority case, never restated), one stanza per third-party part that ships
#   (same globs, its own licence), and every licence id used has text — inline, or
#   a standalone License paragraph (which may point at /usr/share/common-licenses).
authority_id := [c.id | some c in object.get(input, "cases", []); c.kind == "authority"][0]

dep5 := object.get(input, "debian_copyright", {"absent": "no debian_copyright was measured"})

# `absent` is a REASON field: null, "" or missing means "not absent" (the
# convention of `withheld`), so it is read through truth.py — `not dep5.absent`
# took an `"absent": null` as a reason and silenced every L3 rule.
dep5_absent := truth.py(object.get(dep5, "absent", null))

dep5_read if {
	is_object(dep5)
	not dep5_absent
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	dep5_absent
	msg := sprintf("L3: %s", [dep5.absent])
}

deny contains msg if {
	dep5_read
	dep5.format != input.dep5_format
	msg := sprintf("L3: the copyright file's Format is %v, not %s", [dep5.format, input.dep5_format])
}

deny contains msg if {
	dep5_read
	not star_is_authority
	msg := sprintf("L3: no `Files: *` stanza under %v", [authority_id])
}

star_is_authority if {
	some f in dep5.files
	f.files == ["*"]
	f.license == authority_id
}

deny contains msg if {
	dep5_read
	some t in input.third_party
	count(t.files) > 0
	not has_stanza(t)
	msg := sprintf("L3: %s ships (%v) with no %s stanza", [t.what, t.files, t.spdx])
}

has_stanza(t) if {
	some f in dep5.files
	f.files == t.files
	f.license == t.spdx
}

deny contains msg if {
	dep5_read
	some f in dep5.files
	f.copyright == false
	msg := sprintf("L3: stanza %v has no Copyright", [f.files])
}

# METADATA
# title: "L4 — what the measurement could not read is withheld, not judged"
# description: |
#   The measurement always emits `debian_copyright` as an object (a DEP-5 parse,
#   or `{"absent": reason}`) and, per stanza, `files` (list), `license` (string)
#   and `copyright` (bool). A null in any of them is "could not say": a null
#   `copyright` is neither "has no Copyright" (L3) nor fine, and a null
#   `license` is not a licence "used without text".
withheld contains msg if {
	count(object.get(input, "cases", [])) > 0
	not is_object(dep5)
	msg := "L4: debian_copyright was not measured"
}

withheld contains msg if {
	dep5_read
	some f in dep5.files
	some k in unmeasured_stanza(f)
	msg := sprintf("L4: stanza %v: %s was not measured", [object.get(f, "files", null), k])
}

unmeasured_stanza(f) := {k |
	some k, ok in {
		"files": is_array(object.get(f, "files", null)),
		"license": is_string(object.get(f, "license", null)),
		"copyright": is_boolean(object.get(f, "copyright", null)),
	}
	ok == false
}

deny contains msg if {
	dep5_read
	some f in dep5.files
	is_string(f.license)
	not object.get(dep5.licenses, f.license, false)
	msg := sprintf("L3: licence %s is used but carries no text", [f.license])
}

# METADATA
# title: "L2 — a generator names the constant, never a literal"
# description: |
#   One declared id, imported by every emitter: a literal Apache-2.0 is correct
#   today and is the N-th copy the next relicence must find by hand.
deny contains msg if {
	some c in input.cases
	c.kind == "generator"
	c.via != "LICENSE_SPDX"
	msg := sprintf("L2: %s spells its licence (%s) instead of naming emitters.LICENSE_SPDX", [c.where, c.via])
}
