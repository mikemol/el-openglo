# METADATA
# title: "N0 — no roles read admits nothing"
# description: |
#   The measurement is `scripts/check_notify_roles.py --json`: the host's
#   org.kde.notificationmanager Notifications roles, enums and methods, read from
#   the module's qmltypes, beside the roles W46 needs and the roles the harness
#   stub models.
package el.notify_roles

import rego.v1

deny contains msg if {
	not input.withheld
	count(object.get(input, "roles", {})) == 0
	msg := "N0: no roles were read from the module"
}

# METADATA
# title: "N1 — a host without the module is withheld, not judged"
withheld contains msg if {
	input.withheld
	msg := sprintf("N1: %s", [input.withheld])
}

# METADATA
# title: "N2 — every role a capability reads is declared by the host's model"
# description: |
#   A capability written against a role this host's libnotificationmanager does
#   not declare would read undefined forever (the way a single notify-send did
#   before s103) — refused before it is written.
deny contains msg if {
	not input.withheld
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
	not input.withheld
	some r in input.needed
	not r in input.stub_roles
	msg := sprintf("N3: the harness stub does not model %s", [r])
}

# METADATA
# title: "N4 — the model exposes invokeAction, or actions cannot be tapped"
deny contains msg if {
	not input.withheld
	not "invokeAction" in input.methods
	msg := "N4: the model has no invokeAction"
}
