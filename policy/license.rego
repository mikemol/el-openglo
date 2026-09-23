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

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	dep5.absent
	msg := sprintf("L3: %s", [dep5.absent])
}

deny contains msg if {
	not dep5.absent
	dep5.format != input.dep5_format
	msg := sprintf("L3: the copyright file's Format is %v, not %s", [dep5.format, input.dep5_format])
}

deny contains msg if {
	not dep5.absent
	not star_is_authority
	msg := sprintf("L3: no `Files: *` stanza under %v", [authority_id])
}

star_is_authority if {
	some f in dep5.files
	f.files == ["*"]
	f.license == authority_id
}

deny contains msg if {
	not dep5.absent
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
	not dep5.absent
	some f in dep5.files
	not f.copyright
	msg := sprintf("L3: stanza %v has no Copyright", [f.files])
}

deny contains msg if {
	not dep5.absent
	some f in dep5.files
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
