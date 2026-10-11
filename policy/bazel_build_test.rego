package el.bazel_build_test

import data.el.bazel_build as p
import rego.v1

good := {
	"builds": ["BUILD.bazel"],
	"globs": [],
	"inputs": [
		{"build": "BUILD.bazel", "line": 16, "target": "precommit", "attr": "srcs", "label": "gate/precommit.sh", "path": "gate/precommit.sh", "kind": "file"},
		{"build": "BUILD.bazel", "line": 20, "target": "precommit", "attr": "data", "label": "MODULE.bazel", "path": "MODULE.bazel", "kind": "file"},
	],
}

test_admits_named_files if {
	count(p.deny) == 0 with input as good
	count(p.admitted) == 2 with input as good
}

test_b0_refuses_an_empty_population if {
	some msg in p.deny with input as {"builds": [], "globs": [], "inputs": []}
	startswith(msg, "B0:")
}

test_b0_absent_population_is_empty if {
	some msg in p.deny with input as {}
	startswith(msg, "B0:")
}

test_b1_refuses_a_glob if {
	bad := object.union(good, {"globs": [{"build": "BUILD.bazel", "line": 9, "patterns": ["scripts/*.py"]}]})
	some msg in p.deny with input as bad
	startswith(msg, "B1: BUILD.bazel:9 calls glob(")
}

test_b2_refuses_a_directory if {
	bad := object.union(good, {"inputs": [{"build": "BUILD.bazel", "line": 21, "target": "precommit", "attr": "data", "label": "scripts", "path": "scripts", "kind": "directory"}]})
	some msg in p.deny with input as bad
	startswith(msg, "B2: BUILD.bazel:21")
	count(p.admitted) == 0 with input as bad
}

test_b3_refuses_a_gone_file if {
	bad := object.union(good, {"inputs": [{"build": "BUILD.bazel", "line": 22, "target": "precommit", "attr": "srcs", "label": "gate/gone.sh", "path": "gate/gone.sh", "kind": "absent"}]})
	some msg in p.deny with input as bad
	startswith(msg, "B3: BUILD.bazel:22")
}
