# METADATA
# title: "R0 — no keys measured admits nothing"
# description: |
#   The measurement is `scripts/check_config_reach.py --json`: for each kcfg key of the
#   clock, whether the render at the low end of its control differs from the render at
#   the high end (frozen instant, every other key at its default). A setting that
#   changes nothing on screen is a control that does nothing, whatever the kcfg and the
#   page declare about it (W264). An empty population is a broken measurement, not a
#   clock whose settings all work.
package el.config_reach

import rego.v1

deny contains msg if {
	count(object.get(input, "cases", [])) == 0
	object.get(input, "withheld", null) == null
	msg := "R0: no keys were measured; the population is empty, not the settings alive"
}

# METADATA
# title: "R1 — a setting whose two ends render identically is dead"
# description: |
#   Declared INERT (with its reason, in the measurement) is the only way out: a setting
#   that cannot show in one still says so in data the policy reads, never by omission.
inert(c) if {
	is_string(object.get(c, "inert", null))
	count(c.inert) > 0
}

deny contains msg if {
	some c in input.cases
	c.differs == false
	not inert(c)
	msg := sprintf("R1: %s/%s: rendering %v and %v gives the same picture; the setting does nothing", [object.get(c, "mount", "clock"), c.key, c.low, c.high])
}

# METADATA
# title: "R2 — an INERT declaration needs a reason"
deny contains msg if {
	some c in input.cases
	c.differs == false
	object.get(c, "inert", null) != null
	count(object.get(c, "inert", "")) == 0
	msg := sprintf("R2: %s/%s: declared inert with an empty reason", [object.get(c, "mount", "clock"), c.key])
}

# METADATA
# title: "W — a measurement that could not run is withheld"
withheld contains msg if {
	w := object.get(input, "withheld", null)
	w != null
	msg := sprintf("W: %s", [w])
}

withheld contains msg if {
	some c in input.cases
	not is_boolean(object.get(c, "differs", null))
	msg := sprintf("W: %v: differs was not measured", [object.get(c, "key", null)])
}

admitted contains sprintf("%s/%s", [object.get(c, "mount", "clock"), c.key]) if {
	some c in input.cases
	c.differs == true
}

admitted contains sprintf("%s/%s", [object.get(c, "mount", "clock"), c.key]) if {
	some c in input.cases
	c.differs == false
	inert(c)
}
