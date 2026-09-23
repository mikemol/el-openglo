package el.publishing_test

import data.el.publishing as p
import rego.v1

# the selftest's fixture: two KDE Store rows with listed ids, one direct route
good := {"listing": true,
	"cases": [{"emitter": "make_schemes", "rows": 1}, {"emitter": "make_deb", "rows": 1}, {"emitter": "make_css", "rows": 1}],
	"rows": [
		{"emitter": "make_schemes", "venue": "KDE Store", "route": "id 112 [OCS]", "guessed": false, "ids": [{"id": "112", "listed": true}]},
		{"emitter": "make_deb", "venue": "KDE Store", "route": "id 722", "guessed": false, "ids": [{"id": "722", "listed": true}]},
		{"emitter": "make_css", "venue": "the operator's site", "route": "direct", "guessed": false, "ids": []},
	],
}

test_admits_a_routed_table if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 3 with input as good
}

test_b0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "B0:")
}

test_b0_refuses_an_empty_table if {
	some msg in p.deny with input as object.union(good, {"rows": []})
	msg == "B0: catalog/publishing.md has no rows"
}

# the selftest's make_new: an emitter added with no route
test_b1_refuses_an_emitter_without_a_row if {
	bad := object.union(good, {"cases": array.concat(good.cases, [{"emitter": "make_new", "rows": 0}])})
	some msg in p.deny with input as bad
	msg == "B1: make_new has no row in catalog/publishing.md"
	count(p.admitted) == 3 with input as bad
}

# the selftest's id 999: cited, not in the store's taxonomy
test_b2_refuses_an_unlisted_id if {
	bad := object.union(good, {"rows": array.concat(good.rows, [{"emitter": "make_x", "venue": "KDE Store", "route": "id 999", "guessed": false, "ids": [{"id": "999", "listed": false}]}])})
	some msg in p.deny with input as bad
	msg == "B2: make_x: id 999 is not in the OCS listing"
}

# the selftest's id 723?: a guess written into the table
test_b2_refuses_a_guessed_id if {
	bad := object.union(good, {"rows": array.concat(good.rows, [{"emitter": "make_x", "venue": "KDE Store", "route": "id 723?", "guessed": true, "ids": [{"id": "723", "listed": true}]}])})
	some msg in p.deny with input as bad
	msg == "B2: make_x: guessed id in \"id 723?\""
}

# an unlisted id on a NON-store venue is not the store's taxonomy's business
test_b2_admits_an_unlisted_id_off_the_store if {
	ok := object.union(good, {"rows": array.concat(good.rows, [{"emitter": "make_css", "venue": "the operator's site", "route": "id 999", "guessed": false, "ids": [{"id": "999", "listed": false}]}])})
	count(p.deny) == 0 with input as ok
}

# null is truthy to a bare Rego reference: a null listing is not a cached listing,
# and a null guessed is not a guess
test_null_listing_guessed_does_not_fire if {
	bad := object.union(good, {"listing": null, "rows": array.concat(good.rows, [{"emitter": "make_x", "venue": "KDE Store", "route": "id 999", "guessed": null, "ids": [{"id": "999", "listed": false}]}])})
	not "B2: make_x: id 999 is not in the OCS listing" in p.deny with input as bad
	not "B2: make_x: guessed id in \"id 999\"" in p.deny with input as bad
}

test_b2_refuses_a_missing_listing if {
	some msg in p.deny with input as object.union(good, {"listing": false})
	startswith(msg, "B2: no cached OCS listing")
}
