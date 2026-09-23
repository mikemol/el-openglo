# METADATA
# title: "N0 — no nodes measured admits nothing"
# description: |
#   The measurement is `scripts/check_netlist_render.py --json`: every graph
#   node (palette_graph.nodes) and whether it appears in the emitted dot; every
#   edge family, its style colour, and whether that colour reaches the dot and
#   the SVG `dot -Tsvg` renders; the elimination frames; and the interior nodes
#   still carrying edges after the last frame. `render.ok` null is a host fact
#   (graphviz absent) and is WITHHELD, not failed.
#   Weakness: a picture that renders is not a picture that is legible.
package el.netlist_render

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "N0: no graph nodes were measured; the search is broken, not the render clean"
}

deny contains msg if {
	object.get(input, "frames", 0) == 0
	msg := "N0: no elimination frames; the solve did not run"
}

# ⚑ EXACTLY ONCE: a fact the measurement always emits that arrives null (or, for a
# per-item fact, absent) is a could-not-say — WITHHELD, never judged and never
# silently nothing. `not c.in_dot` read null as "present"; `== false` does not.
withheld contains msg if {
	object.get(input, "frames", 0) == null
	msg := "N0: frames was not measured"
}

withheld contains msg if {
	object.get(input, "stuck", []) == null
	msg := "N1: stuck was not measured"
}

withheld contains msg if {
	some c in object.get(input, "cases", [])
	not is_boolean(object.get(c, "in_dot", null))
	msg := sprintf("N2: %v: in_dot was not measured", [object.get(c, "node", null)])
}

withheld contains msg if {
	some f in object.get(input, "families", [])
	not is_boolean(object.get(f, "in_dot", null))
	msg := sprintf("N3: family %v: in_dot was not measured", [object.get(f, "family", null)])
}

withheld contains msg if {
	some f in object.get(input, "families", [])
	not "colour" in object.keys(f)
	msg := sprintf("N3: family %v: colour was not measured", [object.get(f, "family", null)])
}

withheld contains msg if {
	input.render.ok == true
	some f in object.get(input, "families", [])
	is_string(object.get(f, "colour", null))
	not is_boolean(object.get(f, "in_svg", null))
	msg := sprintf("N3: family %v: in_svg was not measured", [object.get(f, "family", null)])
}

# METADATA
# title: "N1 — the sequence eliminates everything eliminable"
deny contains msg if {
	count(object.get(input, "stuck", [])) > 0
	msg := sprintf("N1: %d interior node(s) still carry edges after the sequence ends: %v", [count(input.stuck), input.stuck])
}

# METADATA
# title: "N2 — every node appears in the picture"
# description: |
#   Otherwise the render is a subset pretending to be the graph — the
#   `--edges` hardcoded-family defect.
deny contains msg if {
	some c in input.cases
	c.in_dot == false
	msg := sprintf("N2: node %q is in the graph and not in the render", [c.node])
}

# METADATA
# title: "N3 — every family is distinguishable, in the dot and in the SVG"
# description: |
#   IT MUST RENDER, NOT MERELY PARSE: `edgecolor=` is not a graphviz attribute,
#   so a file carrying it loads, exits 0, and draws every edge default black.
deny contains msg if {
	some f in input.families
	f.colour == null
	msg := sprintf("N3: family %q has no style, so it draws as every other", [f.family])
}

deny contains msg if {
	some f in input.families
	f.colour != null
	f.in_dot == false
	msg := sprintf("N3: family %q styles as %s which is absent from the render", [f.family, f.colour])
}

deny contains msg if {
	input.render.ok == false
	msg := sprintf("N3: the static view does not render: %s", [input.render.detail])
}

deny contains msg if {
	input.render.ok == true
	some f in input.families
	f.colour != null
	f.in_svg == false
	msg := sprintf("N3: family %q's colour %s does not survive into the SVG — the file loads and the colour is not in it", [f.family, f.colour])
}

withheld contains msg if {
	not is_boolean(object.get(object.get(input, "render", {}), "ok", null))
	msg := sprintf("N3: render unverified — %v", [object.get(object.get(input, "render", {}), "detail", "render.ok was not measured")])
}

admitted contains c.node if {
	some c in input.cases
	c.in_dot == true
}
