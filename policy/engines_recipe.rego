# METADATA
# title: "E0 - no recipe measured admits nothing"
# description: |
#   The measurement is `scripts/check_engines_recipe.py --json`: the engine image Containerfile's snapshot
#   pin, whether it is the guest recipe's pin, whether apt reads through that snapshot, whether the install
#   leaves recommends out, the engine packages it lacks, and whether the entrypoint prints both versions.
#   W257; the caller's Containerfile for luthen's self-serve runner (luthen-observability:W328).
# custom:
#   family: gate
package el.engines_recipe

import rego.v1

deny contains "E0: no recipe was measured" if {
	count(object.get(input, "cases", [])) == 0
	count(object.get(input, "withheld", [])) == 0
}

# METADATA
# title: "E1 - the snapshot is a pinned timestamp (an unpinned build is not reproducible)"
deny contains msg if {
	some c in input.cases
	c.snapshot_pinned == false
	msg := sprintf("E1: %s: snapshot %v is not a pinned YYYYMMDDTHHMMSSZ timestamp", [c.recipe, c.snapshot])
}

# METADATA
# title: "E2 - the snapshot is the guest recipe's (one pin, not two)"
deny contains msg if {
	some c in input.cases
	c.snapshot_is_guests == false
	msg := sprintf("E2: %s: snapshot %v is not the guest recipe's %v", [c.recipe, c.snapshot, c.guest_snapshot])
}

# METADATA
# title: "E3 - apt reads through snapshot.debian.org at the pin and no live mirror"
deny contains msg if {
	some c in input.cases
	c.mirror_through_snapshot == false
	msg := sprintf("E3: %s: apt does not read through snapshot.debian.org at the pin, or a live mirror is named", [c.recipe])
}

# METADATA
# title: "E4 - the install leaves recommends out"
deny contains msg if {
	some c in input.cases
	c.no_recommends == false
	msg := sprintf("E4: %s: an apt-get install does not pass --no-install-recommends", [c.recipe])
}

# METADATA
# title: "E5 - Blender and a headless Godot are named"
deny contains msg if {
	some c in input.cases
	some p in c.missing
	msg := sprintf("E5: %s: engine package %s is not in the install", [c.recipe, p])
}

# METADATA
# title: "E6 - the entrypoint prints both versions"
deny contains msg if {
	some c in input.cases
	c.entry_prints_versions == false
	msg := sprintf("E6: %s: the entrypoint does not print both the Blender and the Godot version", [c.recipe])
}

withheld contains msg if {
	some msg in object.get(input, "withheld", [])
}
