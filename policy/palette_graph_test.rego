package el.palette_graph_test

import data.el.palette_graph as p
import rego.v1

good := {
	"cases": [{"id": "fg", "gate": "fg"}, {"id": "neg", "gate": "neg"}, {"id": "view", "gate": null}],
	"emitted": ["fg", "fg_in", "neg", "view"],
	"gate_names": ["fg", "neg"],
	"edges": 3,
	"pairs": {"enforced": {"authority": [["fg", "neg"]], "declared": [["fg", "neg"]]}, "surfaced": {"authority": [], "declared": []}},
}

test_admits_a_total_agreeing_authority if {
	count(p.deny) == 0 with input as good
	p.admitted == {"fg", "neg", "view"} with input as good
}

test_g0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "G0:")
}

# the real first-ship defect: GRID walked as a sequence, 0 emitted keys, a pass printed
test_g0_refuses_zero_emitted_keys if {
	bad := object.union(good, {"emitted": []})
	some msg in p.deny with input as bad
	msg == "G0: 3 nodes but 0 emitted; the search is broken, not the graph clean"
}

test_g0_refuses_zero_edges if {
	some msg in p.deny with input as object.union(good, {"edges": 0})
	msg == "G0: 0 edges; the search is broken, not the graph clean"
}

test_g1_refuses_a_key_nothing_emits if {
	bad := object.union(good, {"cases": array.concat(good.cases, [{"id": "no_such_token", "gate": null}])})
	some msg in p.deny with input as bad
	msg == "G1: no_such_token: emitted key \"no_such_token\" appears in no variant"
	not "no_such_token" in p.admitted with input as bad
}

test_g2_refuses_a_gate_name_cvd_gate_does_not_use if {
	bad := object.union(good, {"cases": [{"id": "fg", "gate": "fg"}, {"id": "neg", "gate": "neg"}, {"id": "view", "gate": "no_such_gate_name"}]})
	some msg in p.deny with input as bad
	msg == "G2: view: gate name \"no_such_gate_name\" is in no ENFORCED/SURFACED pair"
}

test_g2_refuses_a_gate_name_no_node_claims if {
	some msg in p.deny with input as object.union(good, {"gate_names": ["fg", "neg", "visited"]})
	msg == "G2: gate name \"visited\" is used by cvd_gate but claimed by no node"
}

test_g3_refuses_a_pair_only_cvd_gate_declares if {
	bad := object.union(good, {"pairs": {"enforced": {"authority": [["fg", "neg"]], "declared": [["fg", "neg"], ["neg", "visited"]]}}})
	some msg in p.deny with input as bad
	msg == "G3: enforced: cvd_gate declares [\"neg\", \"visited\"] and the authority does not"
}

test_g3_refuses_a_pair_only_the_authority_declares if {
	bad := object.union(good, {"pairs": {"enforced": {"authority": [["fg", "neg"]], "declared": []}}})
	some msg in p.deny with input as bad
	msg == "G3: enforced: the authority declares [\"fg\", \"neg\"] and cvd_gate does not"
}
