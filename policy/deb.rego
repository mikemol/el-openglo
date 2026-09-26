package el.deb

# W79 — the .deb the operator installs by hand builds, dpkg accepts it, and it
# carries everything that was staged. The measurement is scripts/check_deb.py
# --json over luthen's deb_pack output (a digest-pinned Debian image on BuildKit:
# this Gentoo host has no dpkg) beside the staged package root it packed.

import rego.v1

# first rule: an ABSENT or empty population is a broken search, not a clean package
deny contains "D0: no staged file measured: the search is broken" if {
	count(object.get(input, "staged", [])) == 0
	count(object.get(input, "withheld", [])) == 0
}

pack_steps := ["clamp", "build", "info", "contents"]

# D1 — every pack step ran and exited 0 (a step absent from status never ran)
deny contains msg if {
	count(object.get(input, "withheld", [])) == 0
	some s in pack_steps
	code := object.get(object.get(input, "steps", {}), s, null)
	code != 0
	msg := sprintf("D1: pack step %q exited %v (null = never ran)", [s, code])
}

# D2 — every staged file ships: dpkg-deb --contents lists it
deny contains msg if {
	packed := {p | some p in object.get(input, "packed", [])}
	some f in object.get(input, "staged", [])
	not f in packed
	msg := sprintf("D2: %s was staged but is not in the package", [f])
}

# D3 — nothing ships that was not staged (a stale or foreign pack output)
deny contains msg if {
	staged := {p | some p in object.get(input, "staged", [])}
	some f in object.get(input, "packed", [])
	not f in staged
	msg := sprintf("D3: %s is in the package but was not staged: the pack is not of this stage", [f])
}

# D4 — when deb_pack's verdict is supplied, it reads ok and names its checksum
deny contains msg if {
	v := input.verdict
	v.state != "ok"
	msg := sprintf("D4: deb_pack verdict is %q (step %v)", [v.state, object.get(v, "step", "?")])
}

# absent, null or empty all mean the same: no checksum to compare builds by
deny contains "D4: deb_pack verdict carries no sha256" if {
	v := input.verdict
	v.state == "ok"
	object.get(v, "sha256", "") in {"", null}
}

withheld contains msg if {
	some msg in object.get(input, "withheld", [])
}
