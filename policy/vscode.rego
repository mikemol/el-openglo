# METADATA
# title: "V0 — no themes measured admits nothing; every declared variant is measured"
# description: |
#   The measurement is `scripts/check_vscode.py --json`: the declared roster
#   (variant_roster), and per variant what its committed vscode/themes file SAYS —
#   the JSON error (null when it parses), each workbench or token colour that is
#   not its palette role, each colour key no role maps, the theme type against the
#   variant's polarity, whether it equals a fresh emission, and the WCAG ratio of
#   every declared text pair and syntax colour read from the file against its floor.
#   Plus the package.json against the roster and the .vsix packed afresh against the
#   documented layout. W161. Weakness: the files, not VS Code's render.
package el.vscode

import data.el.fmt
import rego.v1

deny contains "V0: no themes were measured; the roster is empty, not the themes sound" if {
	count(object.get(input, "cases", [])) == 0
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	some v in object.get(input, "roster", [])
	not v in {c.id | some c in input.cases}
	msg := sprintf("V0: %s: declared but not measured", [v])
}

# METADATA
# title: "V1 — every declared variant has its theme file, and no theme file is an orphan"
deny contains msg if {
	some c in input.cases
	c.present == false
	msg := sprintf("V1: %s: vscode/themes has no file for this variant", [c.id])
}

deny contains msg if {
	some f in object.get(input, "orphans", [])
	msg := sprintf("V1: orphan theme file %s: no declared variant owns it", [f])
}

# METADATA
# title: "V2 — the theme parses as a JSON object"
deny contains msg if {
	some c in input.cases
	is_string(object.get(c, "parse_error", null))
	msg := sprintf("V2: %s: theme does not parse: %s", [c.id, c.parse_error])
}

# METADATA
# title: "V3 — every colour is its palette role, and every colour key is mapped"
deny contains msg if {
	some c in input.cases
	some w in object.get(c, "wrong_colours", [])
	msg := sprintf("V3: %s: %s = %v, not its role %s = %v", [c.id, w.key, w.got, w.role, w.want])
}

deny contains msg if {
	some c in input.cases
	some w in object.get(c, "wrong_tokens", [])
	msg := sprintf("V3: %s: token %s = %v, not its role %s = %v", [c.id, w.name, w.got, w.role, w.want])
}

deny contains msg if {
	some c in input.cases
	count(object.get(c, "unmapped_keys", [])) > 0
	msg := sprintf("V3: %s: colour key(s) no palette role maps: %v", [c.id, c.unmapped_keys])
}

# METADATA
# title: "V4 — type is dark for an Off variant and light for a Lit one"
deny contains msg if {
	some c in input.cases
	c.parse_error == null
	c.type != c.want_type
	msg := sprintf("V4: %s: type is %v, the variant's polarity wants %v", [c.id, c.type, c.want_type])
}

# METADATA
# title: "V5 — every declared text pair and syntax colour clears its contrast floor"
deny contains msg if {
	some c in input.cases
	some x in object.get(c, "contrast", [])
	is_number(x.ratio)
	x.ratio < x.floor
	msg := sprintf("V5: %s: %s is %s:1, below its %s:1 floor", [c.id, x.pair, fmt.fixed(x.ratio, 2), fmt.fixed(x.floor, 1)])
}

# a declared pair whose colours the theme does not carry is not measured
withheld contains msg if {
	some c in input.cases
	some x in object.get(c, "contrast", [])
	not is_number(x.ratio)
	msg := sprintf("V5: %s: %s was not measured (a colour is absent)", [c.id, x.pair])
}

# METADATA
# title: "V6 — the committed theme is current (equals a fresh emission)"
deny contains msg if {
	some c in input.cases
	c.parse_error == null
	c.current == false
	msg := sprintf("V6: %s: stale; run make_vscode.py", [c.id])
}

# METADATA
# title: "V7 — package.json contributes exactly the roster, files present, uiTheme by polarity, and is current"
deny contains "V7: vscode/package.json is missing" if {
	input.package.present == false
}

deny contains msg if {
	is_string(object.get(input.package, "parse_error", null))
	msg := sprintf("V7: vscode/package.json does not parse: %s", [input.package.parse_error])
}

deny contains msg if {
	some v in object.get(input.package, "missing", [])
	msg := sprintf("V7: package.json does not contribute %s", [v])
}

deny contains msg if {
	some p in object.get(input.package, "extra", [])
	msg := sprintf("V7: package.json contributes %s, which no declared variant owns", [p])
}

deny contains msg if {
	some v in object.get(input.package, "missing_files", [])
	msg := sprintf("V7: package.json names a theme file for %s that is not there", [v])
}

deny contains msg if {
	some v in object.get(input.package, "wrong_ui", [])
	msg := sprintf("V7: %s: uiTheme does not match the variant's polarity", [v])
}

deny contains "V7: vscode/package.json is stale; run make_vscode.py" if {
	input.package.current == false
}

# METADATA
# title: "V8 — the .vsix packed afresh opens and carries the documented layout, equal to the folder"
deny contains msg if {
	input.vsix.opens == false
	msg := sprintf("V8: the packed .vsix does not open: %s", [input.vsix.why])
}

deny contains msg if {
	some n in object.get(input.vsix, "required", [])
	msg := sprintf("V8: the .vsix lacks %s", [n])
}

deny contains msg if {
	some n in object.get(input.vsix, "missing", [])
	msg := sprintf("V8: the .vsix lacks %s, which the folder emits", [n])
}

deny contains msg if {
	some n in object.get(input.vsix, "extra", [])
	msg := sprintf("V8: the .vsix carries %s, which the folder does not emit", [n])
}

deny contains msg if {
	some n in object.get(input.vsix, "differs", [])
	msg := sprintf("V8: the .vsix entry %s differs from the folder's emission", [n])
}

deny contains msg if {
	is_string(object.get(input.vsix, "corrupt_member", null))
	msg := sprintf("V8: the .vsix member %s fails its CRC", [input.vsix.corrupt_member])
}

denied_ids contains c.id if {
	some c in input.cases
	some m in deny
	contains(m, sprintf(": %s:", [c.id]))
}

admitted contains c.id if {
	some c in input.cases
	c.parse_error == null
	not c.id in denied_ids
}
