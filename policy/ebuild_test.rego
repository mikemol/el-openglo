package el.ebuild_test

import data.el.ebuild as p
import rego.v1

good := {
	"markers": [{"path": "metadata/layout.conf", "present": true}, {"path": "profiles/repo_name", "present": true}],
	"ebuild": {"present": true, "missing_vars": [], "pkgcheck": {"rc": 0, "errors": false, "output": ""}, "bash_parse": {"rc": 0, "stderr": ""}},
	"deps": {"portageq": true, "atoms": [{"atom": "dev-python/numpy", "resolves": true}]},
	"staging": {"error": null, "files": 312, "missing_dests": [], "sandboxed": true},
}

test_admits_a_sound_overlay if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	p.admitted == {"el-openglo-9999"} with input as good
}

test_b0_refuses_an_absent_population if {
	some m in p.deny with input as {}
	startswith(m, "B0:")
}

test_b0_refuses_a_missing_marker if {
	inp := object.union(good, {"markers": [{"path": "profiles/repo_name", "present": false}]})
	"B0: overlay marker profiles/repo_name is missing" in p.deny with input as inp
}

test_b1_refuses_unset_variables if {
	inp := object.union(good, {"ebuild": {"missing_vars": ["LICENSE", "SLOT"]}})
	"B1: required variable(s) unset: [\"LICENSE\", \"SLOT\"]" in p.deny with input as inp
}

test_b1_refuses_a_pkgcheck_error if {
	inp := object.union(good, {"ebuild": {"pkgcheck": {"rc": 1, "errors": true, "output": "Error: MissingSlotDep"}}})
	"B1: pkgcheck: Error: MissingSlotDep" in p.deny with input as inp
}

test_b1_refuses_an_unparsable_ebuild if {
	inp := object.union(good, {"ebuild": {"bash_parse": {"rc": 2, "stderr": "syntax error: unexpected end of file"}}})
	"B1: bash -n: syntax error: unexpected end of file" in p.deny with input as inp
}

# pkgcheck absent: withheld beside the admitted package — a SKIP, not a pass of the lint
test_b1_withholds_without_pkgcheck if {
	inp := object.union(good, {"ebuild": {"pkgcheck": null}})
	"B1: pkgcheck is not installed here; the ebuild is bash-parsed only" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
}

test_b2_refuses_an_atom_nobody_provides if {
	inp := object.union(good, {"deps": {"portageq": true, "atoms": [{"atom": "dev-nonesuch/absent", "resolves": false}]}})
	"B2: dev-nonesuch/absent has no visible provider" in p.deny with input as inp
}

test_b2_refuses_a_vacuous_atom_list if {
	inp := object.union(good, {"deps": {"portageq": true, "atoms": []}})
	"B2: the ebuild declares no dependency atom; the resolve arm would be vacuous" in p.deny with input as inp
}

test_b2_withholds_off_gentoo if {
	inp := object.union(good, {"deps": {"portageq": false, "atoms": [{"atom": "dev-python/numpy", "resolves": null}]}})
	"B2: portageq is not installed (not a Gentoo host); atom resolution is unmeasured" in p.withheld with input as inp
	count(p.deny) == 0 with input as inp
}

test_b3_refuses_a_failed_stage if {
	inp := object.union(good, {"staging": {"error": "RuntimeError: make_deb --stage failed", "files": null, "missing_dests": null}})
	"B3: staging failed: RuntimeError: make_deb --stage failed" in p.deny with input as inp
	count(p.admitted) == 0 with input as inp
}

test_b3_refuses_an_empty_tree if {
	inp := object.union(good, {"staging": {"files": 0}})
	"B3: staging produced an EMPTY tree — the packager is broken, not the theme small" in p.deny with input as inp
}

test_b3_refuses_a_missing_destination if {
	inp := object.union(good, {"staging": {"missing_dests": ["usr/share/aurorae/themes/EL-Openglo"]}})
	some m in p.deny with input as inp
	startswith(m, "B3: 1 mapped destination(s) absent")
}

test_b3_withholds_without_sandbox if {
	inp := object.union(good, {"staging": {"sandboxed": false}})
	"B3: sys-apps/sandbox is not on PATH; writes outside the tree are unchecked" in p.withheld with input as inp
}

test_withholds_an_unmeasured_part if {
	inp := object.remove(good, ["staging"])
	"W: staging was not measured" in p.withheld with input as inp
	count(p.admitted) == 0 with input as inp
}
