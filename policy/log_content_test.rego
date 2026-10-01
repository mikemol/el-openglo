package el.log_content_test

import data.el.log_content as p
import rego.v1

ok_call := {"id": "templates/marquee-main.qml:382", "call": "trace", "content": []}

test_admits_structure_only if {
	count(p.deny) == 0 with input as {"files": 1, "cases": [ok_call]}
	p.admitted == {"templates/marquee-main.qml:382"} with input as {"files": 1, "cases": [ok_call]}
}

test_c0_refuses_an_absent_population if {
	"C0: no log call was measured; the template read is broken" in p.deny with input as {}
}

# the 2026-10-01 leak, as it stood: rebuild traced the ticker text
test_c1_refuses_a_traced_ticker if {
	leak := {"id": "templates/marquee-main.qml:377", "call": "trace", "content": ["tickerText"]}
	"C1: templates/marquee-main.qml:377 logs content [\"tickerText\"]; log ids, counts and lengths only" in p.deny with input as {"files": 1, "cases": [ok_call, leak]}
	not "templates/marquee-main.qml:377" in p.admitted with input as {"files": 1, "cases": [ok_call, leak]}
}
