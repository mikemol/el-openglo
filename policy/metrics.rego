# METADATA
# title: "M0 — no scenario measured admits nothing; every declared scenario is measured"
# description: |
#   The measurement (scripts/check_metrics.py --json, W77; not yet built - this
#   policy is the MODEL, written first) runs the metrics plasmoid under stubbed
#   inputs and reports, per scenario, the face it rendered. A scenario is the
#   pair of what luthen's endpoints_query.py returned (the executable DataSource)
#   and what the /api/v1/query GET returned. luthen's contract (2026-10-02):
#   exit 0 + state "answered" carries host and port; exit 1 refused; exit 2
#   declaration unreadable; tool absent off-cluster.
package el.metrics

import rego.v1

# the scenarios the measurement must cover, and the face each one must show
required := {
	"tool-missing": "endpoint-unavailable",
	"tool-refused": "endpoint-unavailable",
	"tool-unreadable": "endpoint-unavailable",
	"query-failed": "unreachable",
	"query-ok": "values",
}

deny contains "M0: no scenario was measured; the population is empty, not the widget sound" if {
	count(object.get(input, "cases", [])) == 0
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	some s, _ in required
	not s in {c.scenario | some c in input.cases}
	msg := sprintf("M0: scenario %q was not measured", [s])
}

# METADATA
# title: "M1 — each scenario shows its declared face"
deny contains msg if {
	some c in input.cases
	want := required[c.scenario]
	c.face != want
	msg := sprintf("M1: %s: the widget shows %q, the contract requires %q", [c.scenario, c.face, want])
}

# METADATA
# title: "M2 — the widget is never blank"
# absent, null and "" all mean the same thing here: the widget drew nothing
deny contains msg if {
	some c in input.cases
	object.get(c, "text", null) in {null, ""}
	msg := sprintf("M2: %s: the widget rendered no text (blank)", [c.scenario])
}

# METADATA
# title: "M3 — the endpoint is never a literal"
# description: |
#   luthen forbids address literals: the emitted QML must carry no host or port of
#   luthen's; the measurement reports any it finds in the package.
deny contains msg if {
	some lit in object.get(input, "address_literals", [])
	msg := sprintf("M3: the package carries an address literal %q; read the endpoint from endpoints_query.py at runtime", [lit])
}

withheld contains msg if {
	some msg in object.get(input, "withheld", [])
}

admitted contains c.scenario if {
	some c in input.cases
	c.face == required[c.scenario]
	not object.get(c, "text", null) in {null, ""}
}
