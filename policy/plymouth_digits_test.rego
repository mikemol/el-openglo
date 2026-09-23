package el.plymouth_digits_test

import data.el.plymouth_digits as p
import rego.v1

# the real tree's 7-seg projection (--table, 2026-09-23)
seg := {
	"0": ["a", "b", "c", "d", "e", "f"], "1": ["b", "c"], "2": ["a", "b", "d", "e", "g"],
	"3": ["a", "b", "c", "d", "g"], "4": ["b", "c", "f", "g"], "5": ["a", "c", "d", "f", "g"],
	"6": ["a", "c", "d", "e", "f", "g"], "7": ["a", "b", "c"], "8": ["a", "b", "c", "d", "e", "f", "g"],
	"9": ["a", "b", "c", "d", "f", "g"],
}

good := {"error": null, "cases": [{"id": d, "substrate": s, "plymouth": s} | some d, s in seg]}

test_admits_a_splash_that_draws_the_substrate if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 10 with input as good
}

test_p0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "P0: no digits were measured")
}

test_p0_refuses_an_unreadable_table if {
	some msg in p.deny with input as {"cases": [], "error": "AttributeError: module 'make_plymouth' has no attribute 'SEVENSEG'"}
	contains(msg, "AttributeError")
}

test_p0_refuses_a_shrunk_population if {
	bad := {"error": null, "cases": [c | some c in good.cases; c.id != "7"]}
	some msg in p.deny with input as bad
	msg == "P0: 9 of 10 digits measured; missing [\"7\"]"
}

# no real divergence is recorded — the silo was found by reading make_plymouth,
# not by this check failing — so the refusal is the class it guards: plymouth's
# private copy of a digit drifting from the substrate (a 7 drawn with the f bar)
test_p1_refuses_a_digit_that_differs if {
	bad := {"error": null, "cases": [object.union(c, {"plymouth": ["a", "b", "c", "f"]}) | some c in good.cases; c.id == "7"]}
	some msg in p.deny with input as bad
	msg == "P1: '7': substrate abc vs plymouth abcf"
}
