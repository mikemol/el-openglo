package el.font_compiler_test

import data.el.font_compiler as fc
import rego.v1

h22 := {"fmt": "22", "ch": "H", "authored": ["b", "c", "e", "f", "g1", "g2"], "compiled": ["b", "c", "e", "f", "g1", "g2"], "agree": true, "declared": false, "class": null, "reason": null}

h7 := {"fmt": "7", "ch": "H", "authored": ["b", "c", "e", "f", "g"], "compiled": ["b", "c", "e", "f", "g"], "agree": true, "declared": false, "class": null, "reason": null}

one22 := {"fmt": "22", "ch": "1", "authored": ["b", "c"], "compiled": ["a1", "a2", "b", "c", "d1", "d2"], "agree": false, "declared": true, "class": "display", "reason": "the 7-segment 1"}

one_decl := {"ch": "1", "class": "display", "reason": "the 7-segment 1", "authored": true, "agree22": false}

good := {
	"font": "LiberationMono-Regular.ttf", "withheld": null,
	"font_sha256": "ab", "font_sha256_in_doc": "ab",
	"classes": ["display", "mid-x-height", "descender", "lattice"],
	"cases": [h22, h7, one22],
	"declarations": [one_decl],
}

test_admits_reproduced_and_declared if {
	count(fc.deny) == 0 with input as good
	count(fc.withheld) == 0 with input as good
	"22-seg H reproduced" in fc.admitted with input as good
	"22-seg 1 declared display" in fc.admitted with input as good
	"1 (display): the 7-segment 1" in fc.conventions with input as good
}

test_f0_refuses_an_absent_population if {
	some msg in fc.deny with input as {}
	startswith(msg, "F0:")
}

test_f0_refuses_a_missing_format if {
	some msg in fc.deny with input as object.union(good, {"cases": [h22, one22]})
	msg == "F0: no 7-seg glyph was measured"
}

test_f1_withholds_a_missing_font if {
	w := {"font": null, "withheld": "no TTF", "cases": [], "declarations": []}
	some msg in fc.withheld with input as w
	startswith(msg, "F1:")
	count(fc.deny) == 0 with input as w
}

test_f1_null_withheld_is_not_held if {
	count(fc.withheld) == 0 with input as good
}

test_f2_refuses_a_document_for_another_font if {
	some msg in fc.deny with input as object.union(good, {"font_sha256_in_doc": "cd"})
	startswith(msg, "F2:")
}

# the planted wrong segment: '8' missing g2, undeclared
test_f4_refuses_an_undeclared_wrong_segment if {
	eight := {"fmt": "22", "ch": "8", "authored": ["a1", "a2", "b", "c", "d1", "d2", "e", "f", "g1", "g2"], "compiled": ["a1", "a2", "b", "c", "d1", "d2", "e", "f", "g1"], "agree": false, "declared": false, "class": null, "reason": null}
	some msg in fc.deny with input as object.union(good, {"cases": [h22, h7, one22, eight]})
	startswith(msg, "F4:")
	contains(msg, "1 of 3, 0.33 of 22-seg reproduced")
}

# null is truthy in rego: an `agree` that is null must not admit
test_f4_refuses_a_null_agree if {
	nul := object.union(h22, {"agree": null})
	some msg in fc.deny with input as object.union(good, {"cases": [nul, h7, one22]})
	startswith(msg, "F4:")
}

test_f5_refuses_an_outgrown_declaration if {
	some msg in fc.deny with input as object.union(good, {"declarations": [object.union(one_decl, {"agree22": true})]})
	startswith(msg, "F5:")
}

test_f6_refuses_an_unknown_class if {
	some msg in fc.deny with input as object.union(good, {"declarations": [object.union(one_decl, {"class": "taste"})]})
	startswith(msg, "F6:")
}

test_f6_refuses_an_empty_reason if {
	some msg in fc.deny with input as object.union(good, {"declarations": [object.union(one_decl, {"reason": ""})]})
	msg == "F6: \"1\" is declared a convention with no reason"
}

test_f7_refuses_a_declaration_for_no_authored_glyph if {
	some msg in fc.deny with input as object.union(good, {"declarations": [object.union(one_decl, {"authored": false})]})
	startswith(msg, "F7:")
}
