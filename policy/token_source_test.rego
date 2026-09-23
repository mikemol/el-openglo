package el.token_source_test

import data.el.token_source as p
import rego.v1

good := {"authorities": ["make_preview", "make_schemes"], "declared": 3, "undeclared": [], "absent": [], "cases": [
	{"file": "make_css.py", "present": true, "reads": ["make_preview"]},
	{"file": "make_wallpaper.py", "present": true, "reads": ["make_schemes"]},
	{"file": "make_notify_marquee.py", "present": true, "reads": ["via make_wallpaper_live"]},
]}

test_admits_a_sourced_roster if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 3 with input as good
}

test_c0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "C0:")
}

# the failure this check found on its first run: make_wallpaper, the oldest
# generator, computing its own colours
test_c2_refuses_make_wallpaper_reading_nothing if {
	bad := object.union(good, {"cases": [good.cases[0], {"file": "make_wallpaper.py", "present": true, "reads": []}]})
	some msg in p.deny with input as bad
	startswith(msg, "C2: make_wallpaper.py reads no palette authority (make_preview, make_schemes)")
	count(p.admitted) == 1 with input as bad
}

# W65: make_css.py removed — a discovered roster said "15 of 15" and exited 0
test_c1_refuses_a_deleted_declared_emitter if {
	bad := object.union(good, {"absent": ["make_css.py"], "cases": [{"file": "make_css.py", "present": false, "reads": []}, good.cases[1]]})
	some m1 in p.deny with input as bad
	m1 == "C1: make_css.py is declared in emitters.ROLES and not in the tree"
	some m2 in p.deny with input as bad
	m2 == "C1: make_css.py is a declared emitter whose file is absent"
}

test_c1_refuses_an_undeclared_generator if {
	some msg in p.deny with input as object.union(good, {"undeclared": ["make_new.py"]})
	msg == "C1: make_new.py is in the tree without a role in emitters.ROLES (3 declared)"
}

# null present is not held: no C2 over an unread file, and not admitted
test_null_present_does_not_fire if {
	inp := object.union(good, {"cases": [
		object.union(good.cases[0], {"present": null}),
		{"file": "make_wallpaper.py", "present": null, "reads": []},
	]})
	d := p.deny with input as inp
	every msg in d {
		not startswith(msg, "C2:")
	}
	count(p.admitted) == 0 with input as inp
}

# exactly once: an emitter with its judged fields null is withheld, never judged
test_all_null_case_withheld_only if {
	inp := object.union(good, {"cases": [{"file": "make_css.py", "present": null, "reads": null}]})
	w := p.withheld with input as inp
	"make_css.py: present was not measured" in w
	not "make_css.py" in p.admitted with input as inp
	d := p.deny with input as inp
	every msg in d {
		not contains(msg, "make_css.py")
	}
}

# N1 C1: a null present is withheld, not "a declared emitter whose file is absent"
test_null_present_withheld_not_c1 if {
	inp := object.union(good, {"cases": [object.union(good.cases[0], {"present": null})]})
	count(p.deny) == 0 with input as inp
	"make_css.py: present was not measured" in p.withheld with input as inp
}

# a present emitter whose reads is null is withheld, not admitted or C2
test_null_reads_withheld if {
	inp := object.union(good, {"cases": [object.union(good.cases[0], {"reads": null})]})
	count(p.deny) == 0 with input as inp
	count(p.admitted) == 0 with input as inp
	"make_css.py: reads was not measured" in p.withheld with input as inp
}
