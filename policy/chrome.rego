# METADATA
# title: "B0 — no manifests measured admits nothing"
# description: |
#   The measurement is `scripts/check_chrome.py --json`: the declared roster
#   (make_schemes.GRID via variant_roster), the colours snapshot's LISTING, and per
#   declared variant what make_chrome.manifest returned — manifest_version, name,
#   each theme colour's value and whether its channels were Python ints, whether
#   the manifest round-trips through json — or the error it raised. A third-party
#   module absent from this host is `withheld`. Weakness: shape, not a browser.
package el.chrome

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	object.get(input, "withheld", null) == null
	msg := sprintf("B0: no manifests were measured (%v); the search is broken, not the theme valid", [object.get(input, "error", null)])
}

withheld contains msg if {
	count(object.get(input, "cases", [])) == 0
	w := object.get(input, "withheld", null)
	w != null
	msg := sprintf("B0: %s — a fact about the machine, not the theme", [w])
}

# METADATA
# title: "B0 — the snapshot holds exactly the declared variants"
deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	some v in input.roster
	not v in {s | some s in input.snapshot}
	msg := sprintf("B0: %s: declared by GRID but absent from the schemes snapshot", [v])
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	some s in input.snapshot
	not s in {v | some v in input.roster}
	msg := sprintf("B0: %s: present in the schemes snapshot but GRID does not declare it", [s])
}

# METADATA
# title: "B1 — every declared variant emits a manifest"
deny contains msg if {
	some c in input.cases
	c.error != null
	msg := sprintf("B1: %s: %s", [c.id, c.error])
}

# METADATA
# title: "B2 — manifest_version 3 and a name"
deny contains msg if {
	some c in emitted
	c.manifest_version != 3
	msg := sprintf("B2: %s: manifest_version is %v, not 3", [c.id, c.manifest_version])
}

deny contains msg if {
	some c in emitted
	not named(c)
	msg := sprintf("B2: %s: no name", [c.id])
}

# METADATA
# title: "B3 — theme.colors is a non-empty map"
deny contains msg if {
	some c in emitted
	not has_colors(c)
	msg := sprintf("B3: %s: theme.colors is missing or empty", [c.id])
}

# METADATA
# title: "B4 — every colour is an RGB triple of ints in 0..255"
deny contains msg if {
	some c in emitted
	has_colors(c)
	some x in c.colors
	not triple(x)
	msg := sprintf("B4: %s: colour '%s' is %v, not an RGB triple in 0..255", [c.id, x.key, x.value])
}

# METADATA
# title: "B5 — the manifest round-trips through JSON"
deny contains msg if {
	some c in emitted
	c.roundtrips != true
	msg := sprintf("B5: %s: the manifest does not serialise as JSON", [c.id])
}

emitted contains c if {
	some c in input.cases
	c.error == null
}

named(c) if {
	c.name != null
	c.name != ""
}

has_colors(c) if {
	c.colors != null
	is_array(c.colors)
	count(c.colors) > 0
}

triple(x) if {
	x.ints == true
	is_array(x.value)
	count(x.value) == 3
	every ch in x.value {
		is_number(ch)
		ch >= 0
		ch <= 255
	}
}

admitted contains c.id if {
	some c in emitted
	c.manifest_version == 3
	named(c)
	has_colors(c)
	every x in c.colors {
		triple(x)
	}
	c.roundtrips == true
}
