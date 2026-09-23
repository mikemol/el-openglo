package el.license_test

import data.el.license as lc
import rego.v1

cases := [
	{"kind": "authority", "where": "emitters.LICENSE_SPDX", "id": "Apache-2.0", "via": "constant"},
	{"kind": "generator", "where": "make_clock.py:63", "id": "Apache-2.0", "via": "LICENSE_SPDX"},
	{"kind": "file", "where": "LICENSE", "id": "Apache-2.0", "via": "text"},
	{"kind": "emitted", "where": "plasma-clock/org.el.segclock/metadata.json KPlugin.License", "id": "Apache-2.0", "via": "json"},
]

test_l0_refuses_a_missing_emitted_kind if {
	some msg in lc.deny with input as {"cases": [c | some c in cases; c.kind != "emitted"]}
	msg == "L0: no emitted declaration was measured"
}

test_l1_refuses_a_stale_emitted_metadata_json if {
	bad := {"kind": "emitted", "where": "plasma-clock/org.el.segclock/metadata.json KPlugin.License", "id": "GPLv3", "via": "json"}
	some msg in lc.deny with input as {"cases": array.concat([c | some c in cases; c.kind != "emitted"], [bad])}
	msg == "L1: plasma-clock/org.el.segclock/metadata.json KPlugin.License declares GPLv3, not Apache-2.0"
}

test_l1_refuses_a_gpl_emitted_desktop_entry if {
	bad := {"kind": "emitted", "where": "sddm/x/metadata.desktop [SddmGreeterTheme] License=", "id": "GPL-3", "via": "desktop"}
	some msg in lc.deny with input as {"cases": array.concat(cases, [bad])}
	startswith(msg, "L1: sddm/x/metadata.desktop")
}

test_l2_does_not_apply_to_emitted if {
	count(lc.deny) == 0 with input as good
	some c in cases
	c.kind == "emitted"
	c.via == "json"
}

fmt :="https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/"

tp := [
	{"what": "KvFlat", "spdx": "GPL-3.0-or-later", "files": ["usr/share/el-openglo/kvantum/*"]},
	{"what": "DSEG", "spdx": "OFL-1.1", "files": []},
]

dep5 := {"format": fmt, "licenses": {"Apache-2.0": true, "GPL-3.0-or-later": true},
	"files": [
		{"files": ["*"], "license": "Apache-2.0", "copyright": true},
		{"files": ["usr/share/el-openglo/kvantum/*"], "license": "GPL-3.0-or-later", "copyright": true},
	]}

good := {"cases": cases, "third_party": tp, "debian_copyright": dep5, "dep5_format": fmt}

with_dep5(d) := object.union(object.remove(good, ["debian_copyright"]), {"debian_copyright": d})

test_l3_refuses_a_deb_without_copyright if {
	some msg in lc.deny with input as with_dep5({"absent": "make_deb has no copyright_text()"})
	msg == "L3: make_deb has no copyright_text()"
}

test_l3_refuses_a_missing_format_header if {
	some msg in lc.deny with input as with_dep5(object.union(dep5, {"format": null}))
	startswith(msg, "L3: the copyright file's Format is null")
}

test_l3_refuses_a_star_stanza_under_another_id if {
	d := object.union(dep5, {"files": [{"files": ["*"], "license": "GPL-3.0-or-later", "copyright": true}, dep5.files[1]]})
	some msg in lc.deny with input as with_dep5(d)
	msg == "L3: no `Files: *` stanza under Apache-2.0"
}

test_l3_refuses_a_shipped_third_party_without_its_stanza if {
	d := object.union(dep5, {"files": [dep5.files[0]]})
	some msg in lc.deny with input as with_dep5(d)
	startswith(msg, "L3: KvFlat ships")
}

test_l3_refuses_a_third_party_under_the_project_licence if {
	d := object.union(dep5, {"files": [dep5.files[0], {"files": ["usr/share/el-openglo/kvantum/*"], "license": "Apache-2.0", "copyright": true}]})
	some msg in lc.deny with input as with_dep5(d)
	startswith(msg, "L3: KvFlat ships")
}

test_l3_refuses_a_licence_without_text if {
	d := object.union(object.remove(dep5, ["licenses"]), {"licenses": {"Apache-2.0": true}})
	some msg in lc.deny with input as with_dep5(d)
	msg == "L3: licence GPL-3.0-or-later is used but carries no text"
}

test_admits_an_apache_tree if {
	count(lc.deny) == 0 with input as good
}

test_l0_refuses_an_absent_population if {
	some msg in lc.deny with input as {}
	msg == "L0: no licence declaration was measured"
}

test_l0_refuses_an_empty_population if {
	some msg in lc.deny with input as {"cases": []}
	msg == "L0: no licence declaration was measured"
}

test_l0_refuses_a_missing_kind if {
	some msg in lc.deny with input as {"cases": [c | some c in cases; c.kind != "file"]}
	msg == "L0: no file declaration was measured"
}

test_l1_refuses_a_gpl_generator if {
	bad := {"kind": "generator", "where": "make_sddm.py:82", "id": "GPLv3", "via": "LICENSE_SPDX"}
	some msg in lc.deny with input as {"cases": array.concat(cases, [bad])}
	startswith(msg, "L1: make_sddm.py:82 declares")
	contains(msg, "GPLv3")
}

test_l1_refuses_a_gpl_licence_file if {
	bad := {"kind": "file", "where": "LICENSE", "id": "GPL-3.0", "via": "text"}
	some msg in lc.deny with input as {"cases": array.concat(cases, [bad])}
	startswith(msg, "L1: LICENSE declares")
}

test_l1_refuses_an_unresolved_declaration if {
	bad := {"kind": "file", "where": "pyproject.toml [project].license", "id": null, "via": "toml"}
	some msg in lc.deny with input as {"cases": array.concat(cases, [bad])}
	msg == "L1: pyproject.toml [project].license declares null, not Apache-2.0"
}

test_l2_refuses_a_literal_even_when_correct if {
	lit := {"kind": "generator", "where": "make_plasma.py:75", "id": "Apache-2.0", "via": "literal"}
	some msg in lc.deny with input as {"cases": array.concat(cases, [lit])}
	startswith(msg, "L2: make_plasma.py:75")
}

test_l2_admits_a_literal_outside_the_generators if {
	count(lc.deny) == 0 with input as object.union(good, {"cases": array.concat(cases, [{"kind": "file", "where": "x", "id": "Apache-2.0", "via": "toml"}])})
}
