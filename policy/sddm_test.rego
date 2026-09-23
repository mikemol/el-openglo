package el.sddm_test

import data.el.sddm as s
import rego.v1

expected := {"user": "bob", "session": 1, "password": "hunter2"}

probe := {"passwordField": true, "passwordEcho": 2, "focusedAtStart": true,
	"clickCall": {"calls": 1, "user": "bob", "password": "hunter2", "session": 1},
	"enterCalls": 2, "failureVisibleAtStart": false, "failureVisible": true,
	"failureText": "Login Failed", "userSelector": true, "sessionSelector": true,
	"userCount": 2, "sessionCount": 2}

clean := {"expected": expected, "cases": [{"id": "EL-Openglo", "rc": 0, "lit_px": 900, "probe": probe}]}

with_probe(p) := {"expected": expected, "cases": [{"id": "EL-Openglo", "rc": 0, "lit_px": 900, "probe": object.union(probe, p)}]}

test_admits_clean if {
	count(s.deny) == 0 with input as clean
	s.admitted == {"EL-Openglo"} with input as clean
}

test_s0_refuses_empty if {
	some msg in s.deny with input as {}
	startswith(msg, "S0:")
}

test_s1_refuses_no_probe if {
	some msg in s.deny with input as {"expected": expected, "cases": [{"id": "EL-Openglo", "rc": 1, "lit_px": 0, "probe": null}]}
	startswith(msg, "S1:")
}

test_s2_refuses_no_lit if {
	some msg in s.deny with input as {"expected": expected, "cases": [{"id": "EL-Openglo", "rc": 0, "lit_px": 0, "probe": probe}]}
	startswith(msg, "S2:")
}

test_s3_refuses_missing_field if {
	some msg in s.deny with input as with_probe({"passwordField": false})
	contains(msg, "no password field")
}

test_s3_refuses_plain_echo if {
	some msg in s.deny with input as with_probe({"passwordEcho": 0})
	contains(msg, "echoes")
}

test_s3_refuses_unfocused if {
	some msg in s.deny with input as with_probe({"focusedAtStart": false})
	contains(msg, "focus")
}

test_s4_refuses_no_login_call if {
	some msg in s.deny with input as with_probe({"clickCall": {"calls": 0, "user": "", "password": "", "session": -1}})
	startswith(msg, "S4:")
}

test_s4_refuses_wrong_session if {
	some msg in s.deny with input as with_probe({"clickCall": {"calls": 1, "user": "bob", "password": "hunter2", "session": 0}})
	startswith(msg, "S4:")
}

test_s5_refuses_dead_enter if {
	some msg in s.deny with input as with_probe({"enterCalls": 1})
	startswith(msg, "S5:")
}

test_s6_refuses_silent_failure if {
	some msg in s.deny with input as with_probe({"failureVisible": false})
	startswith(msg, "S6:")
}

test_s7_refuses_unbound_users if {
	some msg in s.deny with input as with_probe({"userCount": 0})
	startswith(msg, "S7:")
}

test_withheld_only if {
	inp := {"expected": expected, "cases": [{"id": "EL-Openglo", "withheld": "no qml"}]}
	count(s.deny) == 0 with input as inp
	count(s.withheld) == 1 with input as inp
	count(s.admitted) == 0 with input as inp
}

# null passwordField is not held: echo/focus rules judge only a present field
test_null_password_field_does_not_fire if {
	inp := with_probe({"passwordField": null, "passwordEcho": 0, "focusedAtStart": false})
	d := s.deny with input as inp
	every msg in d {
		not contains(msg, "echoes")
		not contains(msg, "does not hold keyboard focus")
	}
}

# a null selector was not MEASURED (the harness always emits a boolean): the case
# is withheld and not admitted — neither bound (admit) nor unbound (S7)
test_null_selector_does_not_admit if {
	inp := with_probe({"userSelector": null})
	s.withheld == {"S8: EL-Openglo: probe.userSelector was not measured"} with input as inp
	count(s.admitted) == 0 with input as inp
	count(s.deny) == 0 with input as inp
	inp2 := with_probe({"sessionSelector": null})
	s.withheld == {"S8: EL-Openglo: probe.sessionSelector was not measured"} with input as inp2
	count(s.admitted) == 0 with input as inp2
}

# N1 fix (S3 `not c.probe.passwordField`): null is not "no password field"
test_null_password_field_withheld_not_s3 if {
	inp := with_probe({"passwordField": null})
	count(s.deny) == 0 with input as inp
	s.withheld == {"S8: EL-Openglo: probe.passwordField was not measured"} with input as inp
	count(s.admitted) == 0 with input as inp
}

# N1 fix (S3 `not c.probe.focusedAtStart`): null is not "does not hold focus"
test_null_focused_at_start_withheld_not_s3 if {
	inp := with_probe({"focusedAtStart": null})
	count(s.deny) == 0 with input as inp
	s.withheld == {"S8: EL-Openglo: probe.focusedAtStart was not measured"} with input as inp
}

# N1 fix (`not c.withheld` in measured): a null withheld REASON must not drop the case
test_null_withheld_case_is_judged if {
	inp := {"expected": expected, "cases": [{"id": "EL-Openglo", "rc": 0, "lit_px": 0, "probe": probe, "withheld": null}]}
	some msg in s.deny with input as inp
	startswith(msg, "S2:")
}

test_all_null_case_withheld_only if {
	nullprobe := {f: null | some f in s.probe_fields}
	inp := {"expected": expected, "cases": [{"id": "EL-Openglo", "rc": null, "lit_px": null, "probe": nullprobe}]}
	count(s.deny) == 0 with input as inp
	count(s.admitted) == 0 with input as inp
	w := s.withheld with input as inp
	count(w) == 10
	"S8: EL-Openglo: lit_px was not measured" in w
	"S8: EL-Openglo: probe.clickCall was not measured" in w
}

test_null_expected_withheld if {
	inp := object.union(clean, {"expected": null})
	s.withheld == {"S8: expected was not measured"} with input as inp
	count(s.deny) == 0 with input as inp
	count(s.admitted) == 0 with input as inp
}

# null withheld is not a withholding
test_null_withheld_does_not_fire if {
	inp := {"expected": expected, "cases": [{"id": "EL-Openglo", "rc": 0, "lit_px": 900, "probe": probe, "withheld": null}]}
	count(s.withheld) == 0 with input as inp
}
