# METADATA
# title: "M0 — no variants measured admits nothing; every declared variant is measured"
# description: |
#   The measurement is `scripts/check_monet.py --json`: whether
#   material-color-utilities is installed (`library`), the declared roster
#   (variant_roster), and per variant Monet's TonalSpot scheme seeded from lit —
#   WCAG of its on_surface/surface and on_primary/primary pairs, the HCT hue
#   between seed and primary, the worst-view dE between its surface and our
#   ground, and the scheme's polarity — or `missing` with a reason. What is NOT
#   claimed: that a Lit variant's surface equals ground — Monet's light surfaces
#   are near-white by design; catalog/android.md records that disagreement.
#   Weakness: the reference derivation, pinned by the library's version.
package el.monet

import data.el.fmt
import rego.v1

aa := 4.5

# degrees of HCT hue between the seed and Monet's primary (TonalSpot keeps hue;
# sRGB rounding moves it a few degrees)
hue_tol := 12.0

# worst-view dE between Monet's dark surface and our ground (measured 2.5-3.4 on
# 2026-09-21)
surface_tol := 5.0

deny contains "M0: no variants were measured; the roster is empty, not Monet in agreement" if {
	object.get(input, "library", true) != false
	count(object.get(input, "cases", [])) == 0
}

withheld contains msg if {
	object.get(input, "library", true) == false
	msg := sprintf("M0: material-color-utilities is not installed here (uv sync --extra research); 0 of %d variants measured", [count(object.get(input, "roster", []))])
}

deny contains msg if {
	count(object.get(input, "cases", [])) > 0
	some v in input.roster
	not v in {c.id | some c in input.cases}
	msg := sprintf("M0: %s: declared but not measured", [v])
}

deny contains msg if {
	some c in input.cases
	c.missing != null
	msg := sprintf("M0: %s: %s", [c.id, c.missing])
}

# METADATA
# title: "M1 — Monet's own text pairs clear WCAG AA"
deny contains msg if {
	some c in measured
	c.text_on_surface < aa
	msg := sprintf("M1: %s: Monet on_surface/surface %s < %s", [c.id, fmt.fixed(c.text_on_surface, 2), fmt.fixed(aa, 1)])
}

deny contains msg if {
	some c in measured
	c.on_primary < aa
	msg := sprintf("M1: %s: Monet on_primary/primary %s < %s", [c.id, fmt.fixed(c.on_primary, 2), fmt.fixed(aa, 1)])
}

# METADATA
# title: "M2 — Monet's primary keeps the seed's hue"
deny contains msg if {
	some c in measured
	c.hue_delta > hue_tol
	msg := sprintf("M2: %s: Monet primary hue drifted %s° from the seed (> %s)", [c.id, fmt.fixed(c.hue_delta, 1), fmt.fixed(hue_tol, 1)])
}

# METADATA
# title: "M3 — on an Off variant, Monet's dark surface lands near ground"
deny contains msg if {
	some c in measured
	c.dark == true
	c.surface_vs_ground_dE > surface_tol
	msg := sprintf("M3: %s: Monet dark surface is %s dE from ground (> %s)", [c.id, fmt.fixed(c.surface_vs_ground_dE, 1), fmt.fixed(surface_tol, 1)])
}

measured contains c if {
	some c in input.cases
	c.missing == null
	c.text_on_surface != null
	c.on_primary != null
	c.hue_delta != null
	c.surface_vs_ground_dE != null
}

deny contains msg if {
	some c in input.cases
	c.missing == null
	not c in measured
	msg := sprintf("M0: %s: a quantity was not measured", [c.id])
}

admitted contains c.id if {
	some c in measured
	c.text_on_surface >= aa
	c.on_primary >= aa
	c.hue_delta <= hue_tol
	surface_ok(c)
}

surface_ok(c) if c.dark != true

surface_ok(c) if c.surface_vs_ground_dE <= surface_tol
