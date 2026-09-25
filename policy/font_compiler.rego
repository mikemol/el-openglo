# METADATA
# title: "F0 — no authored glyph measured admits nothing"
# description: |
#   The measurement is `scripts/check_font_compiler.py --json`: for the host's
#   bundled font, font_compiler's SEGMENT table (the stroke skeleton map-matched
#   onto the 22-lattice; the dot-matrix half was dropped, operator 2026-09-23)
#   against every non-blank authored glyph at 22 and, projected, at 7 — each
#   case carrying whether font_compiler.DECLARED names the glyph a display
#   convention, with its class and reason.
#   The requirement (operator, 2026-09-23): F4, compiled == authored, holds —
#   every remaining difference is a DECLARED convention with a reason, and a
#   declaration the compiler has outgrown must leave.
package el.font_compiler

import data.el.fmt
import data.el.truth
import rego.v1

formats := {"22", "7"}

deny contains msg if {
	not truth.py(object.get(input, "withheld", null))
	count(object.get(input, "cases", [])) == 0
	msg := "F0: no authored glyph was compared against the compiled font; the search is broken, not the font faithful"
}

# METADATA
# title: "F0 — both formats are measured, no fewer"
deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	some f in formats
	count([c | some c in input.cases; c.fmt == f]) == 0
	msg := sprintf("F0: no %s-seg glyph was measured", [f])
}

# METADATA
# title: "F1 — no font on the host is withheld, not judged"
withheld contains msg if {
	truth.py(object.get(input, "withheld", null))
	msg := sprintf("F1: %s", [input.withheld])
}

# METADATA
# title: "F2 — the compiled document is keyed on the font it was compiled from"
deny contains msg if {
	not truth.py(object.get(input, "withheld", null))
	count(object.get(input, "cases", [])) > 0
	input.font_sha256 != input.font_sha256_in_doc
	msg := sprintf("F2: the compiled document names font %s, the file is %s", [input.font_sha256_in_doc, input.font_sha256])
}

# METADATA
# title: "F4 — compiled == authored, or the glyph is a DECLARED convention"
# description: |
#   The operator's requirement for W30. A disagreement nobody declared is a
#   compiler defect or an authored-table defect, and either one is work.
deny contains msg if {
	some c in input.cases
	c.agree != true
	c.declared != true
	msg := sprintf("F4: %s-seg %q compiles to %v, authored %v, and no convention is declared (%s of %s-seg reproduced)",
		[c.fmt, c.ch, c.compiled, c.authored, share(c.fmt), c.fmt])
}

# METADATA
# title: "F5 — a declaration the compiler has outgrown must leave"
deny contains msg if {
	some d in object.get(input, "declarations", [])
	d.agree22 == true
	msg := sprintf("F5: %q is declared a %s convention but compiles to its authored 22-seg set; remove the declaration", [d.ch, d.class])
}

# METADATA
# title: "F6 — a declaration carries a known class and a reason"
deny contains msg if {
	some d in object.get(input, "declarations", [])
	not d.class in object.get(input, "classes", [])
	msg := sprintf("F6: %q is declared with class %v, not one of %v", [d.ch, d.class, object.get(input, "classes", [])])
}

deny contains msg if {
	some d in object.get(input, "declarations", [])
	not truth.py(d.reason)
	msg := sprintf("F6: %q is declared a convention with no reason", [d.ch])
}

# METADATA
# title: "F7 — a declaration names a glyph the authored table has"
deny contains msg if {
	some d in object.get(input, "declarations", [])
	d.authored != true
	msg := sprintf("F7: %q is declared a convention but is not a non-blank authored glyph", [d.ch])
}

share(f) := s if {
	cs := [c | some c in input.cases; c.fmt == f]
	ok := [c | some c in cs; c.agree == true]
	s := sprintf("%d of %d, %s", [count(ok), count(cs), fmt.fixed(count(ok) / count(cs), 2)])
}

admitted contains sprintf("%s-seg %s reproduced", [c.fmt, c.ch]) if {
	some c in input.cases
	c.agree == true
}

admitted contains sprintf("%s-seg %s declared %s", [c.fmt, c.ch, c.class]) if {
	some c in input.cases
	c.agree != true
	c.declared == true
}

# every convention still standing, by name — the list a reviewer audits
conventions contains sprintf("%s (%s): %s", [d.ch, d.class, d.reason]) if {
	some d in object.get(input, "declarations", [])
	d.agree22 != true
}
