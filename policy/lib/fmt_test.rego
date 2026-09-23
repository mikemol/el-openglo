package el.fmt_test

import data.el.fmt
import rego.v1

# the defect this package exists for: a whole number under %.2f
test_sprintf_f_mangles_a_whole_number if {
	contains(sprintf("%.2f", [25]), "%!")
}

test_fixed_prints_a_whole_number if {
	fmt.fixed(25, 2) == "25.00"
	fmt.fixed(3, 1) == "3.0"
	fmt.fixed(1, 4) == "1.0000"
}

test_fixed_rounds_a_fraction if {
	fmt.fixed(3.3333, 2) == "3.33"
	fmt.fixed(2.94, 2) == "2.94"
	fmt.fixed(1.05999, 4) == "1.0600"
	fmt.fixed(0.0712, 4) == "0.0712"
	fmt.fixed(9.96, 1) == "10.0"
}

test_fixed_signs if {
	fmt.fixed(-0.25, 2) == "-0.25"
	fmt.fixed(-0.001, 2) == "0.00"
}

test_fixed_zero_places if {
	fmt.fixed(2.6, 0) == "3"
	fmt.fixed(-2.6, 0) == "-3"
}
