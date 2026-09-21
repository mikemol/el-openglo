# METADATA
# title: Q0 — an empty population admits nothing
# description: |
#   The measurement is `scripts/check_qml_lint.py --json`. A run that measured
#   no documents is a broken search, not a clean tree (CLAUDE.md: "if the
#   population is empty, REFUSE"). Every other rule ranges over
#   input.documents, so this denies first.
package el.qml_lint

import rego.v1

deny contains msg if {
	count(input.documents) == 0
	msg := "Q0: no QML documents were measured; the population is empty, not the tree clean"
}

# METADATA
# title: Q1 — every emitted QML document lints
# description: |
#   qml_sanity keeps only qmllint's ERROR ids (Plasma context properties are
#   not errors). Any kept diagnostic is a measured defect.
deny contains msg if {
	some doc in input.documents
	some d in doc.lint
	msg := sprintf("Q1: %s: %s", [doc.id, d])
}

# METADATA
# title: Q2 — no finite animation binds `running:`
# description: |
#   A finite animation ASSIGNS running=false when it ends, which discards a
#   binding — the marquee's dead-after-first-drain defect (COTYPE s98, live
#   2026-09-22). qmllint cannot see this; the measurement scans animation
#   blocks and reports each finite one whose `running:` is an expression.
deny contains msg if {
	some doc in input.documents
	some b in doc.bound_running
	msg := sprintf("Q2: %s: %s with loops %s binds running: — a finite run overwrites the binding when it ends; start() it instead", [doc.id, b.animation, b.loops])
}

# METADATA
# title: W — a document the host could not render is WITHHELD, not clean and not a defect
# description: |
#   A pair pinned to an absent host file (the marquee's PARITY_FONT) is a
#   fact about the machine. It is reported in its own set so a caller can
#   refuse on it without mistaking it for a measured defect.
withheld contains msg if {
	some doc in input.documents
	doc.withheld
	msg := sprintf("%s: %s", [doc.id, doc.withheld])
}

withheld contains msg if {
	not input.qmllint
	msg := "qmllint is not installed on this host; Q1 measured nothing"
}
