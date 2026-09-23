package el.truth_test

import rego.v1

import data.el.truth

test_null_false_and_empties_are_not_held if {
	not truth.py(null)
	not truth.py(false)
	not truth.py("")
	not truth.py(0)
	not truth.py(0.0)
	not truth.py([])
	not truth.py({})
	not truth.py(set())
}

test_real_values_are_held if {
	truth.py(true)
	truth.py("a reason")
	truth.py(1)
	truth.py(-0.5)
	truth.py(["x"])
	truth.py({"k": null})
	truth.py({1})
}

# the trap this library exists for, shown against the bare reference
test_bare_reference_fires_on_null_py_does_not if {
	c := {"withheld": null}
	c.withheld == null
	not truth.py(c.withheld)
}

fires if truth.py(input.withheld)

# an ABSENT field leaves the body undefined, exactly as the bare reference did
test_absent_field_does_not_fire if {
	not fires with input as {}
	not fires with input as {"withheld": null}
	fires with input as {"withheld": "opa absent"}
}
