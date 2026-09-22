# METADATA
# title: "C0 — no config pages admits nothing"
# description: |
#   The measurement is `scripts/check_config_page.py --json`: per (kcfg, page)
#   template pair, the kcfg's entries and which `cfg_` properties the page declares.
package el.config_page

import rego.v1

deny contains msg if {
	count(object.get(input, "pages", [])) == 0
	msg := "C0: no config pages are measured"
}

# METADATA
# title: "C1 — a page that could not be measured is withheld"
withheld contains msg if {
	some p in input.pages
	p.withheld
	msg := sprintf("C1: %s: %s", [p.page, p.withheld])
}

# METADATA
# title: "C2 — a page declares cfg_<key> for EVERY kcfg entry"
# description: |
#   Plasma's configuration loader sets cfg_<key> on the page for every entry in
#   the schema, whether or not the page draws a control for it; an undeclared one
#   is `Setting initial properties failed` on plasmashell's stderr (operator, live
#   2026-09-22: cfg_traceLog).
deny contains msg if {
	some p in input.pages
	some k in p.keys
	not k.value
	msg := sprintf("C2: %s does not declare cfg_%s", [p.page, k.key])
}

# METADATA
# title: "C3 — a page declares cfg_<key>Default for EVERY kcfg entry"
# description: |
#   The loader also sets cfg_<key>Default (the schema default, for the page's
#   "Defaults" button). Thirteen of these were refused on the live marquee page.
deny contains msg if {
	some p in input.pages
	some k in p.keys
	not k.default
	msg := sprintf("C3: %s does not declare cfg_%sDefault", [p.page, k.key])
}

# METADATA
# title: "C4 — a page with no entries measured nothing"
deny contains msg if {
	some p in input.pages
	not p.withheld
	p.entries == 0
	msg := sprintf("C4: %s: its kcfg has no entries", [p.page])
}
