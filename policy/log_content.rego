# METADATA
# title: "C0 — a template population with no log call admits nothing"
# description: |
#   The measurement is `scripts/check_log_content.py --json`: every console.log/info/
#   warn/debug/error, print( and trace( call in the shipped QML/JS templates, with
#   the content-carrying names its argument references (a `.length` read excepted).
#   Origin (luthen-observability, 2026-10-01): the marquee traced its ticker text -
#   senders, subjects, bodies - into the journal that is shipped to VictoriaLogs, and
#   into the appletsrc on disk.
package el.log_content

import rego.v1

cases := object.get(input, "cases", [])

deny contains "C0: no log call was measured; the template read is broken" if {
	count(cases) == 0
}

# METADATA
# title: "C1 — no log call carries notification content"
# description: |
#   A log line may say how many, how long, which id and what kind - never the text,
#   a summary, a body, a link or a label.
deny contains msg if {
	some c in cases
	count(object.get(c, "content", [])) > 0
	msg := sprintf("C1: %v logs content %v; log ids, counts and lengths only", [c.id, c.content])
}

admitted contains c.id if {
	some c in cases
	count(object.get(c, "content", [])) == 0
}
