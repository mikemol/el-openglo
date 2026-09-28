# METADATA
# title: C0 — an empty population admits nothing
# description: |
#   The measurement is `scripts/check_chrome_zips.py --json`: one case per expected
#   variant. No cases is a broken roster, not a clean package set.
package el.chrome_zips

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	msg := "C0: no Chrome variants were measured; the population is empty, not the packages clean"
}

# METADATA
# title: W — dist/ absent is WITHHELD (publish_browsers --chrome has not run here)
# description: |
#   A missing dist/chrome is a fact about this checkout (the zips are build output),
#   not a defect of the theme. It is withheld so a caller can tell the two apart.
withheld contains msg if {
	count(object.get(input, "cases", [])) > 0
	input.dist == false
	msg := "dist/chrome is absent: run scripts/publish_browsers.py --chrome"
}

built if input.dist == true

# METADATA
# title: C1 — every variant has a zip
deny contains msg if {
	built
	some c in input.cases
	c.exists == false
	msg := sprintf("C1: %s: no dist/chrome/%s.zip", [c.variant, c.variant])
}

# METADATA
# title: C2 — manifest.json sits at the zip root (the Web Store rejects a nested one)
deny contains msg if {
	built
	some c in input.cases
	c.exists == true
	c.root_manifest != true
	msg := sprintf("C2: %s: manifest.json is not at the zip root", [c.variant])
}

# METADATA
# title: C3 — the manifest parses and is manifest_version 3
deny contains msg if {
	built
	some c in input.cases
	c.root_manifest == true
	not c.manifest_version == 3
	msg := sprintf("C3: %s: manifest does not parse as manifest_version 3 (parses=%v, version=%v)", [c.variant, c.parses, c.manifest_version])
}

# METADATA
# title: A — the variants whose zip passed C1-C3
admitted contains c.variant if {
	built
	some c in input.cases
	c.exists == true
	c.root_manifest == true
	c.manifest_version == 3
}
