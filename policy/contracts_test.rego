package el.contracts_test

import data.el.contracts as p
import rego.v1

name := "render_screens.animation"

emits := [
	"file", "variant", "exists", "frames", "width", "axis", "pips", "floor", "shifts", "tears",
	"seamless", "fractional_share", "dominant_period", "dominant_line_share", "spectral_power",
	"period2_share", "logged_steps",
]

good := {"surfaces": [{"surface": name, "emitted": emits, "consumers": [
	{"file": "scripts/check_screens.py", "reads": [{"field": "shifts", "line": 55}, {"field": "exists", "line": 153}]},
]}]}

test_admits_a_kept_contract if {
	count(p.deny) == 0 with input as good
	count(p.withheld) == 0 with input as good
	name in p.admitted with input as good
}

test_k0_refuses_an_absent_population if {
	some msg in p.deny with input as {}
	startswith(msg, "K0:")
}

test_k0_refuses_an_empty_population if {
	some msg in p.deny with input as {"surfaces": []}
	startswith(msg, "K0:")
}

test_k1_refuses_an_undeclared_surface if {
	bad := {"surfaces": [{"surface": "make_x.row", "emitted": ["a"], "consumers": []}]}
	some msg in p.deny with input as bad
	startswith(msg, "K1:")
}

test_k2_refuses_a_read_of_an_undeclared_field if {
	bad := object.union(good, {"surfaces": [{"surface": name, "emitted": emits, "consumers": [
		{"file": "scripts/check_screens.py", "reads": [{"field": "variants", "line": 9}]},
	]}]})
	some msg in p.deny with input as bad
	msg == "K2: scripts/check_screens.py:9 reads variants, which render_screens.animation does not declare"
	not name in p.admitted with input as bad
}

test_k3_refuses_a_declared_field_not_emitted if {
	bad := {"surfaces": [{"surface": name, "emitted": ["file", "variant", "exists"], "consumers": []}]}
	some msg in p.deny with input as bad
	startswith(msg, "K3:")
	contains(msg, "tears")
}

still := "render_screens.still"

still_emits := ["file", "variant", "exists", "grounds", "width", "height", "modal", "distinct"]

# the still rows have no Python consumer (policy/screens.rego reads them, W246): a producer that emits every
# declared field is admitted with an empty consumer list
test_admits_the_still_rows_when_every_declared_field_is_emitted if {
	inp := {"surfaces": [{"surface": still, "emitted": still_emits, "consumers": []}]}
	count(p.deny) == 0 with input as inp
	still in p.admitted with input as inp
}

test_k3_refuses_a_still_row_that_drops_a_declared_field if {
	bad := {"surfaces": [{"surface": still, "emitted": ["file", "variant", "exists", "width", "height", "modal", "distinct"], "consumers": []}]}
	"K3: render_screens.still declares grounds but its producer does not emit it" in p.deny with input as bad
	not still in p.admitted with input as bad
}

scheme := "make_preview.parse_scheme"

scheme_emits := [
	"ground", "panel", "phosphor", "accent", "sel", "window_fg", "focus", "view_bg", "sel_fg", "ghost",
	"ghost_alpha", "ghost_alpha_glanced",
]

# the palette record (W689): a consumer reading declared keys of the returned record is admitted
test_admits_the_palette_record_when_consumers_read_declared_keys if {
	inp := {"surfaces": [{"surface": scheme, "emitted": scheme_emits, "consumers": [
		{"file": "scripts/check_aperture.py", "reads": [{"field": "ground", "line": 48}]},
	]}]}
	count(p.deny) == 0 with input as inp
	scheme in p.admitted with input as inp
}

test_k2_refuses_a_read_of_a_palette_key_parse_scheme_does_not_return if {
	bad := {"surfaces": [{"surface": scheme, "emitted": scheme_emits, "consumers": [
		{"file": "scripts/check_aperture.py", "reads": [{"field": "glow", "line": 48}]},
	]}]}
	"K2: scripts/check_aperture.py:48 reads glow, which make_preview.parse_scheme does not declare" in p.deny with input as bad
	not scheme in p.admitted with input as bad
}

test_k3_refuses_a_palette_key_the_producer_drops if {
	bad := {"surfaces": [{"surface": scheme, "emitted": ["ground"], "consumers": []}]}
	"K3: make_preview.parse_scheme declares sel_fg but its producer does not emit it" in p.deny with input as bad
}

grid := "make_schemes.GRID"

# the token record of every GRID variant (W690): a producer that emits every declared key is admitted with no consumer
test_admits_the_token_record_when_every_declared_key_is_emitted if {
	inp := {"surfaces": [{"surface": grid, "emitted": [k | some k in p.declared[grid].always], "consumers": []}]}
	count(p.deny) == 0 with input as inp
	grid in p.admitted with input as inp
}

test_k3_refuses_a_token_record_that_drops_a_declared_key if {
	bad := {"surfaces": [{"surface": grid, "emitted": [k | some k in p.declared[grid].always; k != "sel_neg"], "consumers": []}]}
	"K3: make_schemes.GRID declares sel_neg but its producer does not emit it" in p.deny with input as bad
	not grid in p.admitted with input as bad
}

test_unreadable_producer_is_withheld_not_judged if {
	inp := {"surfaces": [{"surface": name, "emitted": null, "consumers": [{"file": "c.py", "reads": []}]}]}
	count(p.deny) == 0 with input as inp
	"render_screens.animation: the producer was not readable" in p.withheld with input as inp
	count(p.admitted) == 0 with input as inp
}

test_unreadable_consumer_is_withheld_not_judged if {
	inp := {"surfaces": [{"surface": name, "emitted": emits, "consumers": [{"file": "c.py", "reads": null}]}]}
	count(p.deny) == 0 with input as inp
	"render_screens.animation: consumer c.py was not readable" in p.withheld with input as inp
	count(p.admitted) == 0 with input as inp
}
