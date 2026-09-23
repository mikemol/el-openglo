# METADATA
# title: "G0 — no surface measured admits nothing"
# description: |
#   The measurement is `scripts/check_geometry_source.py --json`: each declared
#   segment surface (wallpaper, live wallpaper, clock, plymouth, marquee),
#   whether it is present, which geometry authorities it imports
#   (segment_topology, make_segment_display, display_types), and which stroke-
#   table names it binds to a LITERAL at module level. An empty roster is
#   stale, not a de-siloed tree.
package el.geometry_source

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "G0: no surfaces were measured; the roster is stale, not the tree de-siloed"
}

# METADATA
# title: "G1 — every declared surface is in the tree"
# description: |
#   A roster file that vanished used to be skipped, which shrank the population
#   without a word. It is now refused.
deny contains msg if {
	some c in input.cases
	not c.present
	msg := sprintf("G1: %s is a declared segment surface and is absent from the tree", [c.file])
}

# METADATA
# title: "G2 — every surface reads the shared geometry"
# description: |
#   GEOMETRY IS A TOKEN SET EXACTLY LIKE COLOUR. Four surfaces once re-implemented
#   the segment shapes while segment_topology, built to supply them, fed none.
deny contains msg if {
	some c in input.cases
	c.present
	count(c.reads) == 0
	msg := sprintf("G2: %s reads no geometry authority (%s)", [c.file, concat(", ", object.get(input, "authorities", []))])
}

# METADATA
# title: "G3 — no surface carries its own stroke table"
# description: |
#   A surface may choose a FORMAT ("7" digits / "22" alphanumeric); it may not
#   choose a SHAPE. The name is not the defect, the literal is: `SEGS =
#   _ST.seg7_svg_grid()` is a derivation and is admitted by the measurement.
deny contains msg if {
	some c in input.cases
	c.present
	count(c.owns) > 0
	msg := sprintf("G3: %s carries its own stroke table (%s) — a re-implementation", [c.file, concat(", ", c.owns)])
}

admitted contains c.file if {
	some c in input.cases
	c.present
	count(c.reads) > 0
	count(c.owns) == 0
}
