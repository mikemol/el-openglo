package el.guest_recipe_test

import rego.v1

import data.el.guest_recipe

good := {"recipe": "r", "snapshot": "20260920T000000Z", "snapshot_pinned": true,
	"mirror_through_snapshot": true, "suite": "trixie", "want_suite": "trixie",
	"missing": [], "forbidden_present": []}

test_empty_denied if {
	count(guest_recipe.deny) == 1 with input as {}
}

test_good_admitted if {
	count(guest_recipe.deny) == 0 with input as {"cases": [good]}
}

test_unpinned_snapshot_denied if {
	"R1: r: snapshot latest is not a pinned YYYYMMDDTHHMMSSZ timestamp" in guest_recipe.deny with input as {"cases": [object.union(good, {"snapshot": "latest", "snapshot_pinned": false})]}
}

test_live_mirror_denied if {
	"R2: r: the mirror is not snapshot.debian.org at {snapshot}" in guest_recipe.deny with input as {"cases": [object.union(good, {"mirror_through_snapshot": false})]}
}

test_wrong_suite_denied if {
	"R3: r: suite bookworm, decided trixie" in guest_recipe.deny with input as {"cases": [object.union(good, {"suite": "bookworm"})]}
}

test_forbidden_package_denied if {
	"R4: r: python3 is declared absent but is in the set" in guest_recipe.deny with input as {"cases": [object.union(good, {"forbidden_present": ["python3"]})]}
}

test_missing_package_denied if {
	"R4: r: decided package jq is not in the set" in guest_recipe.deny with input as {"cases": [object.union(good, {"missing": ["jq"]})]}
}

test_unreadable_withheld if {
	inp := {"cases": [], "withheld": ["recipe unreadable: x"]}
	count(guest_recipe.withheld) == 1 with input as inp
	count(guest_recipe.deny) == 0 with input as inp
}
