# METADATA
# title: "S0 — an unmeasured greeter admits nothing"
# description: |
#   The measurement is `scripts/check_sddm.py --json`: per variant, the SDDM
#   greeter (W66) rendered under stubbed sddm / userModel / sessionModel and
#   DRIVEN — a password typed, the login button clicked, loginFailed fired.
package el.sddm

import rego.v1

cases := object.get(input, "cases", [])

deny contains msg if {
	count(cases) == 0
	msg := "S0: no greeter variant was measured"
}

measured contains c if {
	some c in cases
	not c.withheld
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
	not c.probe.passwordField
	msg := sprintf("S3: %s has no password field", [c.id])
}

deny contains msg if {
	some c in measured
	c.probe.passwordField
	c.probe.passwordEcho != 2
	msg := sprintf("S3: %s password field echoes %v, not TextInput.Password", [c.id, c.probe.passwordEcho])
}

deny contains msg if {
	some c in measured
	c.probe.passwordField
	not c.probe.focusedAtStart
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
	p.userSelector
	p.sessionSelector
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
	c.withheld
	msg := sprintf("%s: %s", [c.id, c.withheld])
}
