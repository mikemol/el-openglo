# ⚑ THIS PAIR IS THE FALSIFIABILITY RECORD. The Python selftest proves the
# MEASUREMENT can see a moved key; these prove the REQUIREMENT refuses and admits
# on the cases it claims to. A check whose all-clear has never been shown to differ
# from its found-something is not a measurement.
package el.action_key_test

import data.el.action_key

_current := {"action": "screens", "state": "current", "key": "aaaa000011112222", "recorded_key": "aaaa000011112222", "n_inputs": 64, "n_outputs": 55, "missing_host": []}

_stale := {"action": "screens", "state": "stale", "key": "bbbb333344445555", "recorded_key": "aaaa000011112222", "n_inputs": 64, "n_outputs": 55, "missing_host": []}

# THE REFUSING CASE — the incident itself: the pictures in the tree were built
# before the grid fix, so the recorded key no longer matches the declared domain.
test_stale_action_denies if {
	r := action_key.deny with input as {"cases": [_stale]}
	count(r) == 1
}

test_current_action_admits if {
	r := action_key.deny with input as {"cases": [_current]}
	count(r) == 0
}

test_current_action_is_admitted if {
	r := action_key.admitted with input as {"cases": [_current]}
	count(r) == 1
}

# ⚑ AN EMPTY POPULATION MUST DENY, NOT PASS. This is the rule that catches a
# broken search reporting a clean tree.
test_empty_population_denies if {
	r := action_key.deny with input as {"cases": []}
	count(r) == 1
}

test_absent_population_denies if {
	r := action_key.deny with input as {}
	count(r) == 1
}

# an action that found no artifacts is a broken output domain, not a clean one
test_zero_outputs_denies if {
	c := object.union(_current, {"n_outputs": 0})
	r := action_key.deny with input as {"cases": [c]}
	count(r) == 1
}

# a key over an empty domain is a constant and can never move
test_zero_inputs_denies if {
	c := object.union(_current, {"n_inputs": 0})
	r := action_key.deny with input as {"cases": [c]}
	count(r) == 1
}

# ⚑ NOT CONFIRMED IS NOT FAILED — neither of these may deny.
test_unrecorded_is_withheld_not_denied if {
	c := object.union(_current, {"state": "unrecorded", "recorded_key": null})
	d := action_key.deny with input as {"cases": [c]}
	w := action_key.withheld with input as {"cases": [c]}
	count(d) == 0
	count(w) == 1
}

test_absent_host_input_is_withheld_not_denied if {
	c := object.union(_current, {"state": "unmeasurable", "missing_host": ["/usr/lib64/qt6/bin/qml"]})
	d := action_key.deny with input as {"cases": [c]}
	w := action_key.withheld with input as {"cases": [c]}
	count(d) == 0
	count(w) == 1
}

# a withheld case BESIDE an admitted one is a SKIP, not a verdict on the tree
test_withheld_beside_admitted if {
	c := object.union(_current, {"action": "schemes", "state": "unrecorded", "recorded_key": null})
	i := {"cases": [_current, c]}
	d := action_key.deny with input as i
	a := action_key.admitted with input as i
	w := action_key.withheld with input as i
	count(d) == 0
	count(a) == 1
	count(w) == 1
}
