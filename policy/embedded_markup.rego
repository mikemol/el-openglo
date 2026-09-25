# METADATA
# title: "E0 — no module scanned admits nothing"
# description: |
#   The measurement is `scripts/check_embedded_markup.py --json`: every tracked
#   top-level module (git_tracked), each markup DOCUMENT found in one by AST walk
#   (a string constant of at least document_lines lines that scripts/identify.py
#   names an artifact MIME, docstrings excluded), the waivers with their reasons,
#   and whether identify.py could be imported at all. Weakness: top-level modules
#   only, and a document split across several short constants is not one.
package el.embedded_markup

import rego.v1

deny contains "E0: no module was scanned; the search is broken, not the tree clean" if {
	count(object.get(input, "cases", [])) == 0
}

# the identifier absent means every string read as not-an-artifact: a scan that cannot see
withheld contains "E0: scripts/identify.py is not importable; no string could be identified, so the scan saw nothing" if {
	input.identifier == false
}

withheld contains "E0: identifier was not measured" if {
	not is_boolean(object.get(input, "identifier", null))
}

waived := {w.path | some w in object.get(input, "waivers", [])}

# METADATA
# title: "E1 — no module embeds a markup document (move it to a template the generator READS)"
deny contains msg if {
	some c in input.cases
	not c.id in waived
	some f in object.get(c, "found", [])
	msg := sprintf("E1: %s:%d embeds a %d-line %s document, un-previewable and un-lintable", [c.id, f.line, f.lines, f.kind])
}

# METADATA
# title: "E2 — every waiver carries a reason"
deny contains msg if {
	some w in object.get(input, "waivers", [])
	not is_string(w.why)
	msg := sprintf("E2: waiver for %s has no reason", [w.path])
}

deny contains msg if {
	some w in object.get(input, "waivers", [])
	is_string(w.why)
	trim_space(w.why) == ""
	msg := sprintf("E2: waiver for %s has no reason", [w.path])
}

withheld contains msg if {
	some c in input.cases
	not is_array(object.get(c, "found", null))
	msg := sprintf("W: %s: found was not measured", [c.id])
}

admitted contains c.id if {
	input.identifier == true
	some c in input.cases
	is_array(object.get(c, "found", null))
	any_ok(c)
}

any_ok(c) if count(c.found) == 0

any_ok(c) if c.id in waived
