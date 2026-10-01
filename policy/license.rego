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
# title: "L5 — NOTICE exists, is exactly what emitters.notice_text() generates, and names every third-party part"
# description: |
#   W118: NOTICE is generated from emitters.THIRD_PARTY, the declaration the DEP-5
#   file reads too. A missing NOTICE, a hand-edited one, or one that omits a part
#   is refused; `missing` names which. A tree with no generator is withheld.
notice := object.get(input, "notice", null)

deny contains "L5: NOTICE is absent; write it with `emitters.py --write-notice`" if {
	is_object(notice)
	notice.present == false
}

deny contains "L5: NOTICE differs from emitters.notice_text(); regenerate it with `emitters.py --write-notice`" if {
	is_object(notice)
	notice.present == true
	notice.matches_generated == false
}

deny contains msg if {
	is_object(notice)
	some what in object.get(notice, "missing", [])
	msg := sprintf("L5: NOTICE does not name the third-party part %q", [what])
}

withheld contains "L5: NOTICE was not measured" if {
	count(object.get(input, "cases", [])) > 0
	not is_object(notice)
}

withheld contains "L5: this tree has no emitters.notice_text(); NOTICE cannot be compared" if {
	is_object(notice)
	notice.generator == false
}

# METADATA
# title: "L6 — every authored source carries the SPDX header"
# description: |
#   W119 (mtools precedent): each tracked, non-symlink *.py starts with
#   `# SPDX-License-Identifier: <authority id>`. An empty population is a broken
#   search; a missing header is refused (write it with `check_license.py
#   --write-headers`); a header naming another id is refused.
headers := object.get(input, "headers", null)

deny contains "L6: no authored source was measured" if {
	is_object(headers)
	object.get(headers, "population", 0) == 0
}

deny contains msg if {
	is_object(headers)
	some f in object.get(headers, "missing", [])
	msg := sprintf("L6: %s carries no SPDX-License-Identifier header; run `check_license.py --write-headers`", [f])
}

deny contains msg if {
	is_object(headers)
	some w in object.get(headers, "wrong", [])
	w.id != authority_id
	msg := sprintf("L6: %s's SPDX header says %v, not %v", [w.file, w.id, authority_id])
}

# W169 (operator, 2026-10-01: "yes, I am the holder"): every authored source also
# carries `# Copyright (c) <year> <holder>` naming the declared holder
# (emitters.COPYRIGHT_HOLDER); `mikemol-pycodemod header --holder` writes it.
deny contains msg if {
	is_object(headers)
	some f in object.get(headers, "no_copyright", [])
	msg := sprintf("L6: %s carries no copyright line; run `check_license.py --write-headers`", [f])
}

deny contains msg if {
	is_object(headers)
	some w in object.get(headers, "wrong_holder", [])
	msg := sprintf("L6: %s's copyright names %v, not the declared holder %v", [w.file, w.holder, headers.holder])
}

withheld contains "L6: a copyright holder is declared but the copyright lines were not measured" if {
	is_object(headers)
	truth.py(object.get(headers, "holder", null))
	not is_array(object.get(headers, "no_copyright", null))
}

withheld contains "L6: authored-source headers were not measured" if {
	count(object.get(input, "cases", [])) > 0
	not is_object(headers)
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
