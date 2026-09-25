# METADATA
# title: "P0 — every declared package was measured"
# description: |
#   The measurement is `scripts/check_package_imports.py --json`: per Plasma
#   package (clock, live wallpaper, marquee), rendered to a temp tree the way its
#   emitter does, the files written, the QML documents under contents/ui, and every
#   type qmllint cannot resolve with that ui directory on the import path (the
#   resolution Plasma does; qmllint's exit code does not report it). `withheld`
#   when qmllint is not on the host. Weakness: type resolution is not a load.
package el.package_imports

import rego.v1

deny contains "P0: no package was measured; the roster is empty, not the packages loadable" if {
	count(object.get(input, "packages", [])) == 0
}

# METADATA
# title: "P1 — a package ships QML documents at all"
# description: |
#   A package whose emitter wrote no contents/ui documents has no types to leave
#   unresolved, so "every type resolves" held for it vacuously.
deny contains msg if {
	some p in input.packages
	not is_string(object.get(p, "withheld", null))
	is_array(p.documents)
	count(p.documents) == 0
	msg := sprintf("P1: %s: no QML document under contents/ui; nothing was linted", [p.package])
}

# METADATA
# title: "P2 — every type a document names resolves where the package puts it"
deny contains msg if {
	some p in input.packages
	not is_string(object.get(p, "withheld", null))
	some u in object.get(p, "missing", [])
	msg := sprintf("P2: %s: %s at %s:%d is not in the package — it would fail to load", [p.package, u.type, u.file, u.line])
}

withheld contains msg if {
	some p in input.packages
	is_string(object.get(p, "withheld", null))
	msg := sprintf("P0: %s: %s", [p.package, p.withheld])
}

withheld contains msg if {
	some p in input.packages
	not is_string(object.get(p, "withheld", null))
	some k in ["documents", "missing"]
	not is_array(object.get(p, k, null))
	msg := sprintf("W: %s: %s was not measured", [p.package, k])
}

admitted contains p.package if {
	some p in input.packages
	not is_string(object.get(p, "withheld", null))
	is_array(object.get(p, "documents", null))
	is_array(object.get(p, "missing", null))
	count(p.documents) > 0
	count(p.missing) == 0
}
