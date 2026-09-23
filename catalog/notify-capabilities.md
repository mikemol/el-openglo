# Notification capabilities on the marquee (W46)

The marquee reads Plasma's public notification model (`org.kde.notificationmanager`,
the feed the stock applet reads). Its contract on this host is MEASURED, not
remembered: `scripts/check_notify_roles.py` parses the module's qmltypes — 49
roles, the `Urgency` / `Type` / `JobState` enums, `invokeAction` — and
`policy/notify_roles.rego` holds every role a capability reads to be declared by
the host (N2) and modelled by the headless stub (N3), so a capability cannot be
written against a role the harness is blind to. The numbers the tool prints are
declaration ordinals; the widget reads roles symbolically.

Operator, 2026-09-22, with the notify-send man page open: "which are we not
achieving?" This table is the answer, one row per capability, each stated as a
relation on the board (relations.md §5a hue, §5b brightness) before any code.

| capability | role(s) | on the board | status |
|---|---|---|---|
| identity, text | `IdRole` `SummaryRole` `BodyRole` `ApplicationNameRole` | the queue keyed by id; summary plain, body parsed to runs (W39/W45) | shipped (s89-s103) |
| urgency | `UrgencyRole` (Low 0 / Normal 1 / Critical 2) | critical: painted in the HOT token (`Kirigami.Theme.activeTextColor`, the ink colour the field reads back) and cycling while it lives — Plasma keeps it live until dismissed; normal: as now; low: light (shrunk) dots at full ink; critical also heavy, underlined dots (W72: opacity and hue are both colour, so neither is the only cue) | shipped s127 (L9) |
| expiry | `ExpiredRole` | drops at the next boundary only (W45); a critical item stays live in the model until dismissed, so it keeps cycling | shipped (W45; s127) |
| replace | (same id, new data) | the id-keyed queue upserts; the new text scrolls once more (W45); a job's progress replace keeps its place (s129) | shipped |
| transient | `TransientRole` | exactly one traversal — dropped after it even while live, never re-queued | shipped s127 (ring case) |
| actions | `ActionNamesRole` `ActionLabelsRole` + `invokeAction(index, id)` | ` [Label]` runs after the text, underlined; `tapAt(x)` resolves a tap to the run and calls `invokeAction` on the row carrying the item — the board is interactive | shipped s128 (L10, M6) |
| job progress | `PercentageRole` `JobStateRole` `TypeRole` (Job 2) | a GAUGE: the percentage history as a series (W48's `seriesToColumns`) painted into the backdrop — one column per sample, the newest at the right — after the job's text; a progress replace keeps the item's place; suspended paints light (shrunk) dots at full ink (W72) | shipped s129 (L11, M7); a stopped job's early drop and suspend/resume/kill as action runs are residue |
| category | `CategoryRole` | a style rule per category (e.g. `device.*` → the field's ring flashes once) | later |
| hints | `HintsRole` | read for `value` (progress) and `urgency` fallbacks; otherwise carried, unread | later |
| icons | `ImageRole` `IconNameRole` | an icon raster is a BACKDROP through the viewport (⊕APERTURE-FIELD; W47's fold) — the app icon rasterised at runtime into column bytes; the app name stands in until then | later |
| reply | `HasReplyActionRole` `ReplyActionLabelRole` … `reply()` | a text field is not a matrix's affordance; the reply action is offered as an action run that opens the stock popup | not planned |

What a capability may NOT do: paint a sender's literal colour (§5a), snap a pip
(§5b), rebuild the board mid-scroll (W38/W45), or read a role the stub lacks (N3).
