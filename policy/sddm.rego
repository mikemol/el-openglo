# METADATA
# title: "S0 — an unmeasured greeter admits nothing"
# description: |
#   The measurement is `scripts/check_sddm.py --json`: per variant, the SDDM
#   greeter (W66) rendered under stubbed sddm / userModel / sessionModel and
#   DRIVEN — a password typed, the login button clicked, loginFailed fired.
#
#   ⚑ EVERY CASE LANDS IN EXACTLY ONE OF withheld / deny / admitted. For a case
#   that was run, check_sddm.py ALWAYS emits `lit_px`, and the harness's probe
#   (scripts/render_qml.py SDDM_HARNESS) ALWAYS emits the fields in
#   `probe_fields` — booleans and counts, never null. Null or absent there, or a
#   null `expected`, is "could not say": S8 withholds it and no rule judges that
#   case. `probe` itself is legitimately null (no probe line: S1), and so are
#   `passwordEcho` / `failureVisibleAtStart` / `failureText` when the element is
#   absent — those stay judged.
package el.sddm

import rego.v1

import data.el.truth

cases := object.get(input, "cases", [])

probe_fields := [
	"passwordField", "focusedAtStart", "userSelector", "sessionSelector",
	"userCount", "sessionCount", "clickCall", "enterCalls", "failureVisible",
]

missing(obj, fields) := {f | some f in fields; object.get(obj, f, null) == null}

case_missing(c) := m if {
	object.get(c, "probe", null) != null
	m := missing(c, ["lit_px"]) | {sprintf("probe.%s", [f]) | some f in missing(c.probe, probe_fields)}
} else := missing(c, ["lit_px"])

# a withholding REASON: null / "" / absent is "not withheld"
held(c) if truth.py(object.get(c, "withheld", null))

expected_measured if object.get(input, "expected", null) != null

deny contains msg if {
	count(cases) == 0
	msg := "S0: no greeter variant was measured"
}

measured contains c if {
	expected_measured
	some c in cases
	not held(c)
	count(case_missing(c)) == 0
}

# METADATA
# title: "S8 — a fact the measurement did not state is withheld, not judged"
withheld contains msg if {
	some c in cases
	not held(c)
	some f in case_missing(c)
	msg := sprintf("S8: %v: %s was not measured", [object.get(c, "id", null), f])
}

withheld contains "S8: expected was not measured" if {
	count(cases) > 0
	not expected_measured
}

# S1 — it rendered, and the harness got its probe back
deny contains msg if {
	some c in measured
	c.probe == null
	msg := sprintf("S1: %s did not render or drive (rc=%v)", [c.id, c.rc])
}

# S2 — lit pixels: the clock mount drew
deny contains msg if {
	some c in measured
	c.lit_px <= 0
	msg := sprintf("S2: %s drew no lit pixels", [c.id])
}

# S3 — the password field exists, echoes as Password (2), holds focus at start
deny contains msg if {
	some c in measured
	c.probe != null
	c.probe.passwordField == false
	msg := sprintf("S3: %s has no password field", [c.id])
}

deny contains msg if {
	some c in measured
	truth.py(c.probe.passwordField)
	c.probe.passwordEcho != 2
	msg := sprintf("S3: %s password field echoes %v, not TextInput.Password", [c.id, c.probe.passwordEcho])
}

deny contains msg if {
	some c in measured
	truth.py(c.probe.passwordField)
	c.probe.focusedAtStart == false
	msg := sprintf("S3: %s password field does not hold keyboard focus at start", [c.id])
}

# S4 — the login path: the click calls sddm.login with the typed password,
# the userModel's lastIndex user and the sessionModel's lastIndex session
deny contains msg if {
	some c in measured
	c.probe != null
	call := c.probe.clickCall
	not login_ok(call, input.expected)
	msg := sprintf("S4: %s login click reached sddm.login as %v, expected %v once", [c.id, call, input.expected])
}

login_ok(call, want) if {
	call.calls == 1
	call.user == want.user
	call.password == want.password
	call.session == want.session
}

# S5 — Enter in the password field also logs in
deny contains msg if {
	some c in measured
	c.probe != null
	c.probe.enterCalls != 2
	msg := sprintf("S5: %s Enter did not call sddm.login (calls=%v)", [c.id, c.probe.enterCalls])
}

# S6 — loginFailed is VISIBLE, and was not visible before
deny contains msg if {
	some c in measured
	c.probe != null
	not failure_ok(c.probe)
	msg := sprintf("S6: %s shows no failure after loginFailed (before=%v after=%v text=%v)", [c.id, c.probe.failureVisibleAtStart, c.probe.failureVisible, c.probe.failureText])
}

failure_ok(p) if {
	p.failureVisibleAtStart == false
	p.failureVisible == true
	count(p.failureText) > 0
}

# S7 — the selectors are bound to the models
deny contains msg if {
	some c in measured
	c.probe != null
	not selectors_ok(c.probe)
	msg := sprintf("S7: %s selectors unbound (users=%v sessions=%v)", [c.id, c.probe.userCount, c.probe.sessionCount])
}

selectors_ok(p) if {
	truth.py(p.userSelector)
	truth.py(p.sessionSelector)
	p.userCount > 0
	p.sessionCount > 0
}

admitted contains c.id if {
	some c in measured
	not denied_id(c.id)
}

denied_id(id) if {
	some msg in deny
	contains(msg, sprintf(" %s ", [id]))
}

withheld contains msg if {
	some c in cases
	truth.py(c.withheld)
	msg := sprintf("%s: %s", [c.id, c.withheld])
}
