# METADATA
# title: "C0 — no config pages admits nothing"
# description: |
#   The measurement is `scripts/check_config_page.py --json`: per (kcfg, page)
#   template pair, the kcfg's entries and which `cfg_` properties the page declares.
package el.config_page

import rego.v1

import data.el.truth

deny contains msg if {
	count(object.get(input, "pages", [])) == 0
	msg := "C0: no config pages are measured"
}

# METADATA
# title: "C1 — a page that could not be measured is withheld"
withheld contains msg if {
	some p in input.pages
	truth.py(p.withheld)
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
# title: "D0 — no display mounts or no display parameters measured nothing"
# description: |
#   W59 (catalog/one-display.md): display_params declares the DISPLAY layer once.
#   An absent population is empty, never admitting.
deny contains msg if {
	count(object.get(object.get(input, "display", {}), "mounts", [])) == 0
	msg := "D0: no display mounts are measured"
}

deny contains msg if {
	count(object.get(object.get(input, "display", {}), "params", [])) == 0
	msg := "D0: no display parameters are declared"
}

# METADATA
# title: "D1 — every mount answers for every display parameter"
# description: |
#   Exposed or withheld-with-reason. A parameter a mount does not mention is an
#   omission nobody can see — the defect W59 exists to end.
deny contains msg if {
	some d in input.display.mounts
	some r in d.params
	r.declared == "absent"
	msg := sprintf("D1: %s neither exposes nor withholds display parameter %s", [d.mount, r.param])
}

# METADATA
# title: "D2 — a withheld parameter says why"
deny contains msg if {
	some d in input.display.mounts
	some r in d.params
	r.declared == "withheld"
	trim_space(object.get(r, "reason", "")) == ""
	msg := sprintf("D2: %s withholds %s with no reason", [d.mount, r.param])
}

# METADATA
# title: "D3 — an exposed parameter is in the emitted kcfg and on the emitted page"
deny contains msg if {
	some d in input.display.mounts
	some r in d.params
	r.declared == "exposed"
	not r.in_kcfg
	msg := sprintf("D3: %s exposes %s as %s, which its kcfg does not carry", [d.mount, r.param, r.spelling])
}

deny contains msg if {
	some d in input.display.mounts
	some r in d.params
	r.declared == "exposed"
	not r.on_page
	msg := sprintf("D3: %s exposes %s as %s, which no page declares (unreachable)", [d.mount, r.param, r.spelling])
}

# METADATA
# title: "D4 — no display key reaches a kcfg undeclared"
deny contains msg if {
	some d in input.display.mounts
	some k in d.stray
	msg := sprintf("D4: %s's kcfg carries display key %s that its declaration does not expose", [d.mount, k])
}

# METADATA
# title: "C4 — a page with no entries measured nothing"
deny contains msg if {
	some p in input.pages
	not p.withheld
	p.entries == 0
	msg := sprintf("C4: %s: its kcfg has no entries", [p.page])
}
