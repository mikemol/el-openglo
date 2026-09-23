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

# ⚑ EVERY PAGE, AND EVERY (mount, param), LANDS IN EXACTLY ONE OF
# withheld / deny / admitted. check_config_page.py ALWAYS emits, for a page it
# read, `entries` (a number) and per key `value` / `default` (booleans); for an
# exposed param, `in_kcfg` / `on_page` (booleans); for every param, `declared`
# (a string). A null or absent one is "could not say": the page / param is
# withheld (C5 / D5) and nothing about it is judged. `not k.value` read null as
# "undeclared" and DENIED it.

pages := object.get(input, "pages", [])

mounts := object.get(object.get(input, "display", {}), "mounts", [])

label(p) := object.get(p, "page", "?")

# read: the page has no withholding reason (null / "" is not one)
read(p) if not truth.py(object.get(p, "withheld", null))

keys(p) := ks if {
	ks := object.get(p, "keys", [])
	is_array(ks)
} else := []

# the fields of a read page that the measurement always emits but did not
unmeasured(p) := ({f |
	some f, t in {"entries": "number", "keys": "array"}
	type_name(object.get(p, f, null)) != t
} | {sprintf("cfg_%v.%s", [object.get(k, "key", "?"), f]) |
	some k in keys(p)
	some f in ["value", "default"]
	not is_boolean(object.get(k, f, null))
})

judged(p) if {
	read(p)
	count(unmeasured(p)) == 0
}

# METADATA
# title: "C1 — a page that could not be measured is withheld"
withheld contains msg if {
	some p in pages
	not read(p)
	msg := sprintf("C1: %s: %s", [label(p), p.withheld])
}

# METADATA
# title: "C5 — a read page with an unmeasured field is withheld, not judged"
withheld contains msg if {
	some p in pages
	read(p)
	count(unmeasured(p)) > 0
	msg := sprintf("C5: %s: %v was not measured", [label(p), sort(unmeasured(p))])
}

page_bad(p) if {
	some k in keys(p)
	k.value == false
}

page_bad(p) if {
	some k in keys(p)
	k.default == false
}

page_bad(p) if p.entries == 0

admitted contains label(p) if {
	some p in pages
	judged(p)
	not page_bad(p)
}

# METADATA
# title: "C2 — a page declares cfg_<key> for EVERY kcfg entry"
# description: |
#   Plasma's configuration loader sets cfg_<key> on the page for every entry in
#   the schema, whether or not the page draws a control for it; an undeclared one
#   is `Setting initial properties failed` on plasmashell's stderr (operator, live
#   2026-09-22: cfg_traceLog).
deny contains msg if {
	some p in pages
	judged(p)
	some k in keys(p)
	k.value == false
	msg := sprintf("C2: %s does not declare cfg_%s", [label(p), object.get(k, "key", "?")])
}

# METADATA
# title: "C3 — a page declares cfg_<key>Default for EVERY kcfg entry"
# description: |
#   The loader also sets cfg_<key>Default (the schema default, for the page's
#   "Defaults" button). Thirteen of these were refused on the live marquee page.
deny contains msg if {
	some p in pages
	judged(p)
	some k in keys(p)
	k.default == false
	msg := sprintf("C3: %s does not declare cfg_%sDefault", [label(p), object.get(k, "key", "?")])
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
	some d in mounts
	some r in mparams(d)
	r.declared == "absent"
	msg := sprintf("D1: %s neither exposes nor withholds display parameter %s", [mlabel(d), plabel(r)])
}

mlabel(d) := object.get(d, "mount", "?")

plabel(r) := object.get(r, "param", "?")

mparams(d) := ps if {
	ps := object.get(d, "params", [])
	is_array(ps)
} else := []

reasoned(r) if {
	s := object.get(r, "reason", null)
	is_string(s)
	trim_space(s) != ""
}

# the fields of a param that the measurement always emits for its `declared`
p_unmeasured(r) := ({"declared" | not object.get(r, "declared", null) in {"exposed", "withheld", "absent"}} | {f |
	r.declared == "exposed"
	some f in ["in_kcfg", "on_page"]
	not is_boolean(object.get(r, f, null))
})

p_judged(r) if count(p_unmeasured(r)) == 0

p_bad(r) if r.declared == "absent"

p_bad(r) if {
	r.declared == "withheld"
	not reasoned(r)
}

p_bad(r) if {
	r.declared == "exposed"
	some f in ["in_kcfg", "on_page"]
	r[f] == false
}

# METADATA
# title: "D5 — a param whose declaration or reach was not measured is withheld"
withheld contains msg if {
	some d in mounts
	some r in mparams(d)
	count(p_unmeasured(r)) > 0
	msg := sprintf("D5: %s/%s: %v was not measured", [mlabel(d), plabel(r), sort(p_unmeasured(r))])
}

admitted contains sprintf("%s/%s", [mlabel(d), plabel(r)]) if {
	some d in mounts
	some r in mparams(d)
	p_judged(r)
	not p_bad(r)
}

# METADATA
# title: "D2 — a withheld parameter says why"
# description: |
#   A null / non-string reason is no reason: `trim_space(null)` is a type error,
#   which made the rule undefined and the param silently neither denied nor admitted.
deny contains msg if {
	some d in mounts
	some r in mparams(d)
	r.declared == "withheld"
	not reasoned(r)
	msg := sprintf("D2: %s withholds %s with no reason", [mlabel(d), plabel(r)])
}

# METADATA
# title: "D3 — an exposed parameter is in the emitted kcfg and on the emitted page"
deny contains msg if {
	some d in mounts
	some r in mparams(d)
	p_judged(r)
	r.declared == "exposed"
	r.in_kcfg == false
	msg := sprintf("D3: %s exposes %s as %v, which its kcfg does not carry", [mlabel(d), plabel(r), object.get(r, "spelling", null)])
}

deny contains msg if {
	some d in mounts
	some r in mparams(d)
	p_judged(r)
	r.declared == "exposed"
	r.on_page == false
	msg := sprintf("D3: %s exposes %s as %v, which no page declares (unreachable)", [mlabel(d), plabel(r), object.get(r, "spelling", null)])
}

# METADATA
# title: "D4 — no display key reaches a kcfg undeclared"
deny contains msg if {
	some d in mounts
	some k in object.get(d, "stray", [])
	msg := sprintf("D4: %s's kcfg carries display key %v that its declaration does not expose", [mlabel(d), k])
}

# METADATA
# title: "C4 — a page with no entries measured nothing"
deny contains msg if {
	some p in pages
	judged(p)
	p.entries == 0
	msg := sprintf("C4: %s: its kcfg has no entries", [label(p)])
}
