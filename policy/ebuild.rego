# METADATA
# title: "B0 — the overlay is a Portage repository"
# description: |
#   The measurement is `scripts/check_ebuild.py --json`: the overlay's two marker
#   files, the ebuild's lint facts (required variables unset, pkgcheck's output
#   when installed, a bash parse), each declared atom and whether Portage sees a
#   provider (portageq false off Gentoo), and the staging of the INDEX tree under
#   sys-apps/sandbox (the error, the file count, the mapped destinations absent,
#   whether the sandbox confined it). Weakness: staging uses this checkout's
#   Python, not the ebuild's BDEPEND; only an emerge proves that set.
package el.ebuild

import rego.v1

deny contains "B0: no overlay marker was measured; the overlay is unread, not sound" if {
	count(object.get(input, "markers", [])) == 0
}

deny contains msg if {
	some m in input.markers
	m.present == false
	msg := sprintf("B0: overlay marker %s is missing", [m.path])
}

# METADATA
# title: "B1 — the ebuild exists, sets every required variable, and lints clean"
deny contains "B1: the ebuild is missing" if {
	input.ebuild.present == false
}

deny contains msg if {
	count(object.get(input.ebuild, "missing_vars", [])) > 0
	msg := sprintf("B1: required variable(s) unset: %v", [input.ebuild.missing_vars])
}

deny contains msg if {
	is_object(input.ebuild.pkgcheck)
	pkgcheck_failed
	msg := sprintf("B1: pkgcheck: %s", [input.ebuild.pkgcheck.output])
}

pkgcheck_failed if input.ebuild.pkgcheck.rc != 0

pkgcheck_failed if input.ebuild.pkgcheck.errors == true

deny contains msg if {
	is_object(input.ebuild.bash_parse)
	input.ebuild.bash_parse.rc != 0
	msg := sprintf("B1: bash -n: %s", [input.ebuild.bash_parse.stderr])
}

withheld contains "B1: pkgcheck is not installed here; the ebuild is bash-parsed only" if {
	input.ebuild.present == true
	input.ebuild.pkgcheck == null
}

# METADATA
# title: "B2 — every declared atom has a visible provider (the overlay in the repo set)"
deny contains "B2: the ebuild declares no dependency atom; the resolve arm would be vacuous" if {
	input.ebuild.present == true
	count(object.get(input.deps, "atoms", [])) == 0
}

deny contains msg if {
	input.deps.portageq == true
	some a in input.deps.atoms
	a.resolves == false
	msg := sprintf("B2: %s has no visible provider", [a.atom])
}

withheld contains "B2: portageq is not installed (not a Gentoo host); atom resolution is unmeasured" if {
	input.deps.portageq == false
}

# METADATA
# title: "B3 — staging the index produces a non-empty tree with every mapped destination"
deny contains msg if {
	is_string(input.staging.error)
	msg := sprintf("B3: staging failed: %s", [input.staging.error])
}

deny contains "B3: staging produced an EMPTY tree — the packager is broken, not the theme small" if {
	input.staging.error == null
	input.staging.files == 0
}

deny contains msg if {
	input.staging.error == null
	count(object.get(input.staging, "missing_dests", [])) > 0
	msg := sprintf("B3: %d mapped destination(s) absent after staging: %v", [count(input.staging.missing_dests), input.staging.missing_dests])
}

withheld contains "B3: sys-apps/sandbox is not on PATH; writes outside the tree are unchecked" if {
	input.staging.sandboxed == false
}

withheld contains msg if {
	some k in ["markers", "ebuild", "deps", "staging"]
	object.get(input, k, null) == null
	msg := sprintf("W: %s was not measured", [k])
}

# one case: the package. Admitted when nothing denies and every part was measured.
admitted contains "el-openglo-9999" if {
	count(deny) == 0
	every k in ["markers", "ebuild", "deps", "staging"] {
		object.get(input, k, null) != null
	}
}
