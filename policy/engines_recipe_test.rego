package el.engines_recipe_test

import rego.v1

import data.el.engines_recipe

good := {
	"recipe": "r", "snapshot": "20260920T000000Z", "snapshot_pinned": true,
	"guest_snapshot": "20260920T000000Z", "snapshot_is_guests": true,
	"mirror_through_snapshot": true, "no_recommends": true, "missing": [], "entry_prints_versions": true,
}

test_empty_denied if {
	count(engines_recipe.deny) == 1 with input as {}
}

test_good_admitted if {
	count(engines_recipe.deny) == 0 with input as {"cases": [good]}
}

test_unpinned_snapshot_denied if {
	"E1: r: snapshot latest is not a pinned YYYYMMDDTHHMMSSZ timestamp" in engines_recipe.deny with input as {"cases": [object.union(good, {"snapshot": "latest", "snapshot_pinned": false})]}
}

test_pin_that_is_not_the_guests_denied if {
	"E2: r: snapshot 20250101T000000Z is not the guest recipe's 20260920T000000Z" in engines_recipe.deny with input as {"cases": [object.union(good, {"snapshot": "20250101T000000Z", "snapshot_is_guests": false})]}
}

test_live_mirror_denied if {
	"E3: r: apt does not read through snapshot.debian.org at the pin, or a live mirror is named" in engines_recipe.deny with input as {"cases": [object.union(good, {"mirror_through_snapshot": false})]}
}

test_recommends_denied if {
	"E4: r: an apt-get install does not pass --no-install-recommends" in engines_recipe.deny with input as {"cases": [object.union(good, {"no_recommends": false})]}
}

test_missing_engine_denied if {
	"E5: r: engine package blender is not in the install" in engines_recipe.deny with input as {"cases": [object.union(good, {"missing": ["blender"]})]}
}

test_silent_entrypoint_denied if {
	"E6: r: the entrypoint does not print both the Blender and the Godot version" in engines_recipe.deny with input as {"cases": [object.union(good, {"entry_prints_versions": false})]}
}

test_unreadable_withheld if {
	inp := {"cases": [], "withheld": ["Containerfile unreadable: x"]}
	count(engines_recipe.withheld) == 1 with input as inp
	count(engines_recipe.deny) == 0 with input as inp
}
