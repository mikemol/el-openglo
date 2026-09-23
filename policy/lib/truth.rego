# METADATA
# title: "truth — what a bare reference MEANT: the measurement's own truthiness"
# description: |
#   REGO NULL IS TRUTHY. An expression that is only a reference (`c.withheld`,
#   `input.parsed`) succeeds whenever the value is defined and not `false` — so
#   null, "", 0, [] and {} all fire it. Every measurement a policy reads is a
#   Python check's --json, and the author of `c.withheld` meant Python's
#   bool(c.withheld): None, False, "", 0, and an empty list / dict / set are NOT
#   held. py(x) is that predicate, stated once. An ABSENT field stays undefined,
#   exactly as the bare reference was.
#
#   scripts/check_rego_lint.py counts a bare VALUE reference as a finding
#   (policy/rego_lint.rego T1); `truth.py(x)` or an explicit comparison is the fix.
#
#   ⚑ policy/lib/, NOT policy/: a library has no check_<name>.py (see fmt.rego).
package el.truth

import rego.v1

py(x) if {
	x != null
	x != false
	x != ""
	x != 0
	not _empty(x)
}

_empty(x) if {
	is_array(x)
	count(x) == 0
}

_empty(x) if {
	is_object(x)
	count(x) == 0
}

_empty(x) if {
	is_set(x)
	count(x) == 0
}
