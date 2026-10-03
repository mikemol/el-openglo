# METADATA
# title: "D0 — no variant measured admits nothing"
# description: |
#   The measurement is `scripts/check_android_clock.py --json`: per variant the palette
#   declares (variant_roster), whether catalog/android/clock/<variant>.json exists and
#   parses, the sections it lacks, the palette roles that differ from make_schemes.GRID,
#   the geometry sections that differ from segment_topology / display_types, the digits
#   without a mask, whether it equals a fresh make_android_clock emission, and orphan
#   files nobody declares. W193.
package el.android_clock

import rego.v1

deny contains "D0: no variant was measured; the roster is empty, not the clock complete" if {
	count(object.get(input, "cases", [])) == 0
	count(object.get(input, "withheld", [])) == 0
}

# METADATA
# title: "D1 — every declared variant has its file"
deny contains msg if {
	some c in input.cases
	c.present == false
	msg := sprintf("D1: %s: catalog/android/clock has no file for this variant", [c.variant])
}

# METADATA
# title: "D2 — the file parses as a JSON object"
deny contains msg if {
	some c in input.cases
	c.present == true
	c.parse_error != null
	msg := sprintf("D2: %s: unparseable: %s", [c.variant, c.parse_error])
}

# METADATA
# title: "D3 — every required section is present, and every digit has a mask"
deny contains msg if {
	some c in input.cases
	c.present == true
	c.parse_error == null
	some k in c.missing_keys
	msg := sprintf("D3: %s: section %s is missing", [c.variant, k])
}

deny contains msg if {
	some c in input.cases
	c.present == true
	c.parse_error == null
	some d in c.digit_gaps
	msg := sprintf("D3: %s: digit %s has no segment mask", [c.variant, d])
}

# METADATA
# title: "D4 — every palette role equals the make_schemes.GRID token it is read from"
deny contains msg if {
	some c in input.cases
	c.present == true
	c.parse_error == null
	some r in c.palette_mismatch
	msg := sprintf("D4: %s: palette.%s does not trace to make_schemes.GRID", [c.variant, r])
}

# METADATA
# title: "D5 — geometry and display equal segment_topology and display_types"
deny contains msg if {
	some c in input.cases
	c.present == true
	c.parse_error == null
	some s in c.geometry_mismatch
	msg := sprintf("D5: %s: %s does not trace to its authority", [c.variant, s])
}

# METADATA
# title: "D6 — the committed file is current (byte-equal to a fresh emission)"
deny contains msg if {
	some c in input.cases
	c.present == true
	c.parse_error == null
	c.current == false
	msg := sprintf("D6: %s: stale; run make_android_clock.py", [c.variant])
}

# METADATA
# title: "D7 — no file in the directory belongs to no declared variant"
deny contains msg if {
	some f in object.get(input, "orphans", [])
	msg := sprintf("D7: orphan file %s: no declared variant owns it", [f])
}

withheld contains msg if {
	some msg in object.get(input, "withheld", [])
}

admitted contains c.variant if {
	some c in input.cases
	c.present == true
	c.parse_error == null
	count(c.missing_keys) == 0
	count(c.digit_gaps) == 0
	count(c.palette_mismatch) == 0
	count(c.geometry_mismatch) == 0
	c.current == true
}
