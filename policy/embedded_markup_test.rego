package el.embedded_markup_test

import data.el.embedded_markup as p
import rego.v1

doc := {"line": 12, "kind": "image/svg+xml", "lines": 40}

good := {"identifier": true, "document_lines": 8, "waivers": [], "cases": [
	{"id": "make_wallpaper.py", "found": []},
	{"id": "make_clock.py", "found": []},
]}

test_admits_a_clean_tree if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	p.admitted == {"make_wallpaper.py", "make_clock.py"} with input as good
}

test_e0_refuses_an_empty_population if {
	"E0: no module was scanned; the search is broken, not the tree clean" in p.deny with input as object.union(good, {"cases": []})
	some m in p.deny with input as {}
	startswith(m, "E0:")
}

# the silent hole: no identifier means nothing could be seen — withheld, nothing admitted
test_e0_withholds_a_scan_without_the_identifier if {
	inp := object.union(good, {"identifier": false})
	some m in p.withheld with input as inp
	startswith(m, "E0: scripts/identify.py is not importable")
	count(p.admitted) == 0 with input as inp
}

test_e1_refuses_an_embedded_document if {
	inp := object.union(good, {"cases": [{"id": "make_wallpaper.py", "found": [doc]}]})
	"E1: make_wallpaper.py:12 embeds a 40-line image/svg+xml document, un-previewable and un-lintable" in p.deny with input as inp
	count(p.admitted) == 0 with input as inp
}

test_e1_admits_a_waived_embedding if {
	inp := {"identifier": true, "document_lines": 8,
		"waivers": [{"path": "make_wallpaper.py", "why": "the SVG is the test fixture itself"}],
		"cases": [{"id": "make_wallpaper.py", "found": [doc]}]}
	count(p.deny) == 0 with input as inp
	p.admitted == {"make_wallpaper.py"} with input as inp
}

test_e2_refuses_a_waiver_without_a_reason if {
	inp := object.union(good, {"waivers": [{"path": "make_clock.py", "why": "  "}]})
	"E2: waiver for make_clock.py has no reason" in p.deny with input as inp
}

test_e2_refuses_a_null_reason if {
	inp := object.union(good, {"waivers": [{"path": "make_clock.py", "why": null}]})
	"E2: waiver for make_clock.py has no reason" in p.deny with input as inp
}

test_all_null_case_withheld_only if {
	inp := {"identifier": true, "document_lines": 8, "waivers": [], "cases": [{"id": "make_clock.py", "found": null}]}
	"W: make_clock.py: found was not measured" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
	count(p.admitted) == 0 with input as inp
}
