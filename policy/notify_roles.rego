# METADATA
# title: "N0 — no roles read admits nothing"
# description: |
#   The measurement is `scripts/check_notify_roles.py --json`: the host's
#   org.kde.notificationmanager Notifications roles, enums and methods, read from
#   the module's qmltypes, beside the roles W46 needs and the roles the harness
#   stub models.
#
#   ⚑ EXACTLY ONCE: the input is one judgement. `withheld` is a withholding
#   REASON (null / "" / absent = not withheld). When it is not withheld the
#   measurement always emits roles (object), needed, stub_roles and methods
#   (lists); one of those null or absent is a could-not-say, WITHHELD by name,
#   and the rule that reads it does not judge.
package el.notify_roles

import rego.v1

import data.el.truth

# the host read the module (a null / "" withheld is not a reason)
measured if not truth.py(object.get(input, "withheld", null))

field_ok("roles") if is_object(object.get(input, "roles", null))

field_ok(f) if {
	f in {"needed", "stub_roles", "methods"}
	is_array(object.get(input, f, null))
}

withheld contains msg if {
	measured
	some f in ["roles", "needed", "stub_roles", "methods"]
	not field_ok(f)
	msg := sprintf("N0: %s was not measured", [f])
}

deny contains msg if {
	measured
	field_ok("roles")
	count(input.roles) == 0
	msg := "N0: no roles were read from the module"
}

# METADATA
# title: "N1 — a host without the module is withheld, not judged"
withheld contains msg if {
	truth.py(input.withheld)
	msg := sprintf("N1: %s", [input.withheld])
}

# METADATA
# title: "N2 — every role a capability reads is declared by the host's model"
# description: |
#   A capability written against a role this host's libnotificationmanager does
#   not declare would read undefined forever (the way a single notify-send did
#   before s103) — refused before it is written.
deny contains msg if {
	measured
	field_ok("roles")
	field_ok("needed")
	some r in input.needed
	not r in object.keys(input.roles)
	msg := sprintf("N2: the host's model does not declare %s", [r])
}

# METADATA
# title: "N3 — every role a capability reads is modelled by the harness stub"
# description: |
#   check_marquee_live's stub stands in for the model headless; a role the widget
#   reads that the stub lacks makes the harness blind to that capability.
deny contains msg if {
	measured
	field_ok("stub_roles")
	field_ok("needed")
	some r in input.needed
	not r in input.stub_roles
	msg := sprintf("N3: the harness stub does not model %s", [r])
}

# METADATA
# title: "N4 — the model exposes invokeAction, or actions cannot be tapped"
deny contains msg if {
	measured
	field_ok("methods")
	not "invokeAction" in input.methods
	msg := "N4: the model has no invokeAction"
}
