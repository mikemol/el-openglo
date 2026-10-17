# METADATA
# title: "B0 — no BUILD file measured admits nothing"
# description: |
#   The measurement is `scripts/check_bazel_build.py --json`: every tracked BUILD / BUILD.bazel
#   file, every `glob()` call in it, and every literal file label in `srcs` / `data` with whether
#   it is a file, a directory or absent. The operator rule (2026-10-06): BUILD inputs are named
#   files, never a glob and never a directory (W487). The names come from mtools' `select_tracked`,
#   a call the measurement does not resolve, so what it refuses is what bypasses the generator.
# custom:
#   family: gate
package el.bazel_build

import rego.v1

deny contains msg if {
	count(object.get(input, "builds", [])) == 0
	msg := "B0: no BUILD file was measured; the population is empty, not the tree faithfully named"
}

# METADATA
# title: "B1 — a glob() makes the input set whatever the disk holds"
deny contains msg if {
	some g in object.get(input, "globs", [])
	msg := sprintf("B1: %s:%d calls glob(%v); inputs are named files from select_tracked, never a glob", [g.build, g.line, g.patterns])
}

# METADATA
# title: "B2 — a directory is not a named input"
deny contains msg if {
	some i in object.get(input, "inputs", [])
	i.kind == "directory"
	msg := sprintf("B2: %s:%d target %q names the directory %q in %s; name its files", [i.build, i.line, i.target, i.label, i.attr])
}

# METADATA
# title: "B3 — a named input that is not on disk"
deny contains msg if {
	some i in object.get(input, "inputs", [])
	i.kind == "absent"
	msg := sprintf("B3: %s:%d target %q names %q in %s and it is not a file here", [i.build, i.line, i.target, i.label, i.attr])
}

admitted contains sprintf("%s:%d:%s", [i.build, i.line, i.label]) if {
	some i in object.get(input, "inputs", [])
	i.kind == "file"
}
