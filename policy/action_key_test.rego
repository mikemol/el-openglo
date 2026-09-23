# ⚑ THIS PAIR IS THE FALSIFIABILITY RECORD. The Python selftest proves the
# MEASUREMENT can see a moved key; these prove the REQUIREMENT refuses and admits
# on the cases it claims to. A check whose all-clear has never been shown to differ
# from its found-something is not a measurement.
package el.action_key_test

import data.el.action_key

_current := {"action": "screens", "state": "current", "key": "aaaa000011112222", "recorded_key": "aaaa000011112222", "n_inputs": 64, "n_outputs": 55, "missing_host": [], "n_unresolved": 0, "n_undeclared_domains": 0, "undeclared_outputs": [], "declared_absent": []}

# ⚑ THE OUTPUT BOUNDARY, BOTH ORIENTATIONS. These DENY rather than withhold: an
# undeclared output is a defect in the action's own declaration, which its author
# can close by naming the file — unlike an unresolved edge, which is a limit of
# the scanner.
test_undeclared_output_denies if {
	c := object.union(_current, {"undeclared_outputs": ["strip.png", "README.md"]})
	r := action_key.deny with input as {"cases": [c]}
	count(r) == 1
}

test_declared_but_absent_output_denies if {
	c := object.union(_current, {"declared_absent": ["clock-EL-Amber.png"]})
	r := action_key.deny with input as {"cases": [c]}
	count(r) == 1
}

test_matching_output_boundary_denies_nothing if {
	r := action_key.deny with input as {"cases": [_current]}
	count(r) == 0
}

_stale := {"action": "screens", "state": "stale", "key": "bbbb333344445555", "recorded_key": "aaaa000011112222", "n_inputs": 64, "n_outputs": 55, "missing_host": [], "n_unresolved": 0, "n_undeclared_domains": 0, "undeclared_outputs": [], "declared_absent": []}

# ⚑ THE RESIDUE CASES. A key over an under-covered domain WITHHOLDS and never
# denies: a false positive in the residue costs one file declared uncovered, a
# false negative costs a wrong verdict.
test_unresolved_edges_withhold_not_deny if {
	c := object.union(_current, {"n_unresolved": 21})
	i := {"cases": [c]}
	d := action_key.deny with input as i
	w := action_key.withheld with input as i
	count(d) == 0
	count(w) == 1
}

test_undeclared_domains_withhold_not_deny if {
	c := object.union(_current, {"n_undeclared_domains": 2})
	i := {"cases": [c]}
	d := action_key.deny with input as i
	w := action_key.withheld with input as i
	count(d) == 0
	count(w) == 1
}

# ⚑ AND A FULLY-COVERED DOMAIN MUST WITHHOLD NOTHING — otherwise the rule above
# can never retire and every run looks equally uncovered.
#
# ⚑ THE LIVENESS CONJUNCT IS NOT PEDANTRY (linux-sources-9c, 2026-09-22, adding
# it to their own retirement arm and driving it red twice): an empty residue over
# a domain that scanned NOTHING proves only that the scanner did nothing. Without
# asserting the population in the same breath, "the residue retired" and "the
# reader is dead" render identically — the very collapse this arm repairs,
# relocated one level up. Their mutation table: clean AND live (1/0/0) green;
# real residue (2/1/1) red; zero residue over nothing scanned (0/0/0) RED.
#
# ⚑ AND IT IS UNTESTED HERE UNTIL IT MATTERS. screens, schemes and wallpapers all
# carry non-zero residue today, so the liveness half would stay unexercised right
# up to the day one of them reaches zero — which is the day it has to mean
# something. That is this repo's "0 of 0 is not agreement", as a policy arm.
test_a_clean_domain_withholds_nothing_and_was_alive_doing_it if {
	i := {"cases": [_current]}
	w := action_key.withheld with input as i
	d := action_key.deny with input as i
	a := action_key.admitted with input as i
	count(w) == 0
	count(d) == 0
	_current.n_inputs > 0     # the population, asserted BEFORE the outcome
	_current.n_outputs > 0
	count(a) == 1             # and the case was actually judged, not merely silent
}

# the other half of the conjunction, driven red: a domain with NO inputs must not
# be able to buy silence by having nothing to say
test_an_empty_domain_cannot_pass_as_clean if {
	c := object.union(_current, {"n_inputs": 0})
	d := action_key.deny with input as {"cases": [c]}
	count(d) == 1
}

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
# ⚑ THE HOST CASES. An unpinned host withholds for a host-seeing action and says
# nothing about a pure one; an uncomputable host identity DENIES.
test_unpinned_host_withholds_for_host_seeing_action if {
	c := object.union(_current, {"sees_host": true})
	i := {"cases": [c], "host": {"kind": "unpinned", "detail": "3 of 3 source(s)"}}
	d := action_key.deny with input as i
	w := action_key.withheld with input as i
	count(d) == 0
	count(w) == 1
}

test_unpinned_host_is_silent_for_a_pure_action if {
	c := object.union(_current, {"sees_host": false})
	i := {"cases": [c], "host": {"kind": "unpinned", "detail": "3 of 3 source(s)"}}
	w := action_key.withheld with input as i
	count(w) == 0
}

test_pinned_host_withholds_nothing if {
	c := object.union(_current, {"sees_host": true})
	i := {"cases": [c], "host": {"kind": "pinned", "detail": "oci/Containerfile"}}
	w := action_key.withheld with input as i
	count(w) == 0
}

test_unmeasurable_host_denies if {
	c := object.union(_current, {"sees_host": true})
	i := {"cases": [c], "host": {"kind": "unmeasurable", "detail": "no host fingerprint source is readable"}}
	d := action_key.deny with input as i
	count(d) == 1
}

# ⚑ PER-OUTPUT CURRENCY (W61). The screens action is keyed one output at a time;
# the requirement judges the stale LIST, one denial per stale picture.
_per := object.union(_current, {"per_output": true, "n_keyed_outputs": 56, "stale_outputs": [], "unrecorded_outputs": []})

# REFUSING: one picture's inputs moved — exactly that picture is denied, by name
test_one_stale_output_denies_by_name if {
	c := object.union(_per, {"state": "stale", "stale_outputs": ["clock-EL-Amber.png"]})
	r := action_key.deny with input as {"cases": [c]}
	count(r) == 1
	some m in r
	contains(m, "clock-EL-Amber.png")
}

# REFUSING: each stale output is its own denial (n of m, not one blanket verdict)
test_each_stale_output_denies if {
	c := object.union(_per, {"state": "stale", "stale_outputs": ["clock-EL-Amber.png", "sheet-EL-Amber.png", "strip.png"]})
	r := action_key.deny with input as {"cases": [c]}
	count(r) == 3
}

# REFUSING: the FACT beats the summary — a measurement that calls itself current
# while listing a stale output is still denied, and is not admitted
test_stale_output_denies_even_if_summary_says_current if {
	c := object.union(_per, {"stale_outputs": ["pinholes-EL-Azure.png"]})
	i := {"cases": [c]}
	d := action_key.deny with input as i
	a := action_key.admitted with input as i
	count(d) == 1
	count(a) == 0
}

# ADMITTING: every output keyed and current — no denial, judged and admitted
test_all_outputs_current_admits if {
	i := {"cases": [_per]}
	d := action_key.deny with input as i
	a := action_key.admitted with input as i
	count(d) == 0
	count(a) == 1
}

# WITHHELD, NOT DENIED: an output never recorded is unmeasured, not stale
test_unrecorded_output_withholds_not_denies if {
	c := object.union(_per, {"state": "unrecorded", "unrecorded_outputs": ["README.md"]})
	i := {"cases": [c]}
	d := action_key.deny with input as i
	w := action_key.withheld with input as i
	count(d) == 0
	count(w) == 1
}

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
